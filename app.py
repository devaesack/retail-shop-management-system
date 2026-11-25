
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)
from db import get_connection
from datetime import timedelta

from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = "retailshop123"

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM admins
            WHERE username=%s
            AND password=%s
        """,
        (username, password))

        admin = cur.fetchone()

        cur.close()
        conn.close()

        if admin:

            session['user'] = username

            return redirect('/dashboard')

        else:
             return render_template(
        'login.html',
        error='Invalid username or password'
    )

    return render_template('login.html')
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
     return redirect('/')

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT COUNT(*)
    FROM sales
    """)

    total_sales = cur.fetchone()[0]
    cur.execute("""
    SELECT COALESCE(SUM(total_amount),0)
    FROM sales
    """)

    total_revenue = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*)
    FROM sales
    WHERE DATE(sale_date)=CURRENT_DATE
    """)

    today_sales = cur.fetchone()[0]
    
    # Total Products
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]

    # Total Stock
    cur.execute("SELECT SUM(stock) FROM products")
    total_stock = cur.fetchone()[0]

    # Low Stock Items
    cur.execute("SELECT COUNT(*) FROM products WHERE stock < 50")
    low_stock = cur.fetchone()[0]
    cur.execute("""
        SELECT product_name, stock
        FROM products
        WHERE stock <= 50
        ORDER BY stock
        """)

    low_stock_products = cur.fetchall()

    cur.execute("""
    SELECT
    p.product_name,
    SUM(s.quantity) AS total_qty

    FROM sales s

    JOIN products p
    ON s.product_id = p.id

   GROUP BY p.product_name

   ORDER BY total_qty DESC

   LIMIT 1
   """)

    top_product = cur.fetchone()

    cur.execute("""
    SELECT
    customer_name,
    p.product_name,
    s.total_amount

    FROM sales s

    JOIN products p
    ON s.product_id = p.id

    ORDER BY s.id DESC

    LIMIT 5
    """)

    recent_sales = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        total_sales=total_sales,
        low_stock_products=low_stock_products,
        total_revenue=total_revenue,
        today_sales=today_sales,
        top_product=top_product,
        recent_sales=recent_sales
    )
@app.route('/products')
def products():

    search = request.args.get('search', '')

    conn = get_connection()
    cur = conn.cursor()

    if search:

        cur.execute("""
            SELECT *
            FROM products
            WHERE product_name ILIKE %s
            ORDER BY id
        """, ('%' + search + '%',))

    else:

        cur.execute("""
            SELECT *
            FROM products
            ORDER BY id
        """)

    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'products.html',
        products=products
    )

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():

    if request.method == 'POST':

        product_name = request.form['product_name']
        category = request.form['category']
        price = request.form['price']
        stock = request.form['stock']

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO products
            (product_name, category, price, stock)
            VALUES (%s, %s, %s, %s)
        """,
        (product_name, category, price, stock))

        conn.commit()

        cur.close()
        conn.close()

        return redirect('/products')

    return render_template('add_product.html')
@app.route('/delete_product/<int:id>')
def delete_product(id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM products WHERE id=%s",
        (id,)
    )

    conn.commit()

    cur.close()
    conn.close()

    return redirect('/products')

@app.route('/edit_product/<int:id>',
           methods=['GET','POST'])
def edit_product(id):

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        product_name = request.form['product_name']
        category = request.form['category']
        price = request.form['price']
        stock = request.form['stock']

        cur.execute("""
            UPDATE products
            SET product_name=%s,
                category=%s,
                price=%s,
                stock=%s
            WHERE id=%s
        """,
        (
            product_name,
            category,
            price,
            stock,
            id
        ))

        conn.commit()

        cur.close()
        conn.close()

        return redirect('/products')

    cur.execute(
        "SELECT * FROM products WHERE id=%s",
        (id,)
    )

    product = cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        'edit_product.html',
        product=product
    )
@app.route('/billing', methods=['GET', 'POST'])
def billing():

    conn = get_connection()
    cur = conn.cursor()

    if request.method == 'POST':

        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        customer_name = request.form['customer_name']

        # Get product details
        cur.execute("""
            SELECT product_name, price, stock
            FROM products
            WHERE id = %s
        """, (product_id,))

        product = cur.fetchone()

        product_name = product[0]
        price = product[1]
        stock = product[2]

        # Check stock
        if quantity > stock:
            return "Not enough stock available!"

        total_amount = price * quantity

        # Save sale
        cur.execute("""
            INSERT INTO sales
            (customer_name,
            product_id,
            quantity,
            total_amount)

            VALUES (%s,%s,%s,%s)
        """,
           (
            customer_name,
            product_id,
            quantity,
            total_amount
                           ))

        # Reduce stock
        cur.execute("""
            UPDATE products
            SET stock = stock - %s
            WHERE id = %s
        """,
        (quantity, product_id))

        conn.commit()

        cur.close()
        conn.close()

        return render_template(
             'bill_success.html',
             customer_name=customer_name,
             product_name=product_name,
             quantity=quantity,
             total_amount=total_amount
)

    # Load products
    cur.execute("""
        SELECT id, product_name
        FROM products
        ORDER BY product_name
    """)

    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'billing.html',
        products=products
    )
@app.route('/sales_history')
def sales_history():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
                SELECT s.id,
                s.customer_name,
               p.product_name,
               s.quantity,
               s.total_amount,
               s.sale_date
        FROM sales s
        JOIN products p
        ON s.product_id = p.id
        ORDER BY s.id DESC
    """)

    sales = cur.fetchall()

    formatted_sales = []

    for sale in sales:

        formatted_sales.append(
            (
                sale[0],
                sale[1],
                sale[2],
                sale[3],
                sale[4],
                (sale[5] +timedelta(hours=5, minutes=30))
                .strftime('%d-%m-%Y %I:%M %p')
            )
        )

    cur.close()
    conn.close()

    return render_template(
        'sales_history.html',
        sales=formatted_sales
    )
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/')

@app.route('/low_stock')
def low_stock():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name,
               stock
        FROM products
        WHERE stock <= 50
        ORDER BY stock ASC
    """)

    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'low_stock.html',
        products=products
    )


if __name__ == '__main__':
    app.run(debug=True)