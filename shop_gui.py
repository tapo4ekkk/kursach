import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from datetime import datetime

# -------------------------
# Подключение к MySQL
# -------------------------
conn = mysql.connector.connect(
    host="5.183.188.132",
    user="db_vgu_student",
    password="thasrCt3pKYWAYcK",
    database="db_vgu_test4"
)
cursor = conn.cursor()

# -------------------------
# Вспомогательные функции
# тестовый B
# -------------------------
def commit():
    try:
        conn.commit()
    except Exception as e:
        messagebox.showerror("Ошибка БД", str(e))

def clear_workspace():
    """Очищает правую рабочую часть"""
    for w in right_frame.winfo_children():
        w.destroy()

def refresh_treeview(tree, query, params=None):
    """Заполнить tree результатом запроса"""
    for r in tree.get_children():
        tree.delete(r)
    cursor.execute(query, params or ())
    for row in cursor.fetchall():
        tree.insert("", tk.END, values=row)

def get_main_hall_id():
    cursor.execute("SELECT id FROM 69420warehouses WHERE type='основной зал' LIMIT 1;")
    res = cursor.fetchone()
    return res[0] if res else None

def load_products_tree(tree, only_hall=False, only_storage=False):
    """Загружает товары в Treeview с фильтрацией по наличию"""
    for r in tree.get_children():
        tree.delete(r)

    cursor.execute("""
        SELECT p.id, p.name, c.name, p.price, 
               p.quantity_hall, p.quantity_storage
        FROM 69420products p
        LEFT JOIN 69420categories c ON p.category_id = c.id
        ORDER BY p.id;
    """)

    rows = cursor.fetchall()
    for pid, name, cname, price, hall_qty, storage_qty in rows:
        total_qty = hall_qty + storage_qty

        if only_hall:
            # Показываем ТОЛЬКО товары, где quantity_hall > 0
            if hall_qty > 0:
                tree.insert("", tk.END, values=(pid, name, cname, price, hall_qty))

        elif only_storage:
            # Показываем ТОЛЬКО товары, где quantity_storage > 0
            if storage_qty > 0:
                tree.insert("", tk.END, values=(pid, name, cname, price, storage_qty))

        else:
            # Во "Все товары" показываем ВСЕ, даже с нулевыми остатками
            tree.insert("", tk.END, values=(pid, name, cname, price, hall_qty, storage_qty, total_qty))

def load_categories_combo(combo):
    cursor.execute("SELECT id, name FROM 69420categories;")
    cats = cursor.fetchall()
    combo['values'] = [f"{c[0]} - {c[1]}" for c in cats]
    return cats

def add_category_action(entry, combo_refresh=None):
    name = entry.get().strip()
    if not name:
        messagebox.showwarning("Внимание", "Введите название категории!")
        return
    try:
        cursor.execute("INSERT INTO 69420categories (name) VALUES (%s);", (name,))
        commit()
        entry.delete(0, tk.END)
        if combo_refresh:
            load_categories_combo(combo_refresh)
        messagebox.showinfo("Успех", "Категория добавлена!")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def add_product_action(name_entry, cat_combo, price_entry, qty_entry, wholesale_entry, products_tree=None):
    try:
        name = name_entry.get().strip()
        if not name:
            raise ValueError("Введите название товара")

        cat = cat_combo.get().strip()
        if not cat or " - " not in cat:
            raise ValueError("Выберите категорию")

        category_id = int(cat.split(" - ")[0])

        # Розничная цена
        price_str = price_entry.get().strip()
        if not price_str:
            raise ValueError("Введите розничную цену")
        price = float(price_str)
        if price <= 0:
            raise ValueError("Розничная цена не может быть нулевой или отрицательной")

        # Количество
        qty_str = qty_entry.get().strip()
        if not qty_str:
            raise ValueError("Введите количество")
        qty = int(qty_str)
        if qty < 0:
            raise ValueError("Количество не может быть отрицательным")

        # Закупочная цена
        wholesale_str = wholesale_entry.get().strip()
        if not wholesale_str:
            wholesale = 0.0
        else:
            wholesale = float(wholesale_str)
            if wholesale <= 0:
                raise ValueError("Закупочная цена не может быть отрицательной или равной нулю")

        # Добавляем товар
        cursor.execute("""
            INSERT INTO 69420products (name, category_id, price, quantity_hall, wholesale_price)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, category_id, price, qty, wholesale))

        commit()
        messagebox.showinfo("Успех", "Товар добавлен!")

        # Очистка полей
        name_entry.delete(0, tk.END)
        cat_combo.set('')
        price_entry.delete(0, tk.END)
        qty_entry.delete(0, tk.END)
        wholesale_entry.delete(0, tk.END)

        if products_tree:
            load_products_tree(products_tree)

    except ValueError as ve:
        messagebox.showerror("Ошибка", str(ve))
    except Exception as e:
        messagebox.showerror("Ошибка БД", str(e))
        conn.rollback()

def delete_product_action(products_tree):
    sel = products_tree.selection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите товар для удаления")
        return

    item = products_tree.item(sel[0])['values']
    pid = item[0]
    pname = item[1]

    if not messagebox.askyesno("Подтвердите", f"Удалить товар '{pname}' и все связанные записи?"):
        return

    try:
        # Удаляем связанные записи (в правильном порядке из-за FK)
        cursor.execute("DELETE FROM 69420sales WHERE product_id = %s;", (pid,))
        cursor.execute("DELETE FROM 69420purchases WHERE product_id = %s;", (pid,))
        # stock_movements удалена — эту строку убираем полностью

        # Удаляем сам товар
        cursor.execute("DELETE FROM 69420products WHERE id = %s;", (pid,))

        commit()

        # Обновляем таблицу
        load_products_tree(products_tree)

        messagebox.showinfo("Успех", "Товар удалён")

    except Exception as e:
        messagebox.showerror("Ошибка БД", str(e))
        conn.rollback()

def edit_product_action(products_tree):
    sel = products_tree.selection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите товар для редактирования")
        return
    item = products_tree.item(sel[0])['values']
    pid = item[0]

    # Получаем актуальные данные из БД (с новыми полями)
    cursor.execute("""
        SELECT id, name, category_id, price, quantity_hall, quantity_storage, COALESCE(wholesale_price,0)
        FROM 69420products WHERE id = %s;
    """, (pid,))
    rec = cursor.fetchone()
    if not rec:
        messagebox.showerror("Ошибка", "Товар не найден в БД")
        return

    _, name0, cat_id0, price0, hall_qty0, storage_qty0, wprice0 = rec

    win = tk.Toplevel(root)
    win.title(f"Редактировать товар — ID {pid}")
    win.geometry("420x360")

    tk.Label(win, text="Название:").pack(anchor="w", padx=10, pady=4)
    name_e = tk.Entry(win); name_e.pack(fill=tk.X, padx=10); name_e.insert(0, name0)

    tk.Label(win, text="Категория:").pack(anchor="w", padx=10, pady=4)
    cat_cb = ttk.Combobox(win, state="readonly"); cat_cb.pack(fill=tk.X, padx=10)
    cats = load_categories_combo(cat_cb)
    for c in cats:
        if c[0] == cat_id0:
            cat_cb.set(f"{c[0]} - {c[1]}")
            break

    tk.Label(win, text="Цена (розничная):").pack(anchor="w", padx=10, pady=4)
    price_e = tk.Entry(win); price_e.pack(fill=tk.X, padx=10); price_e.insert(0, str(price0))

    tk.Label(win, text="Закупочная цена:").pack(anchor="w", padx=10, pady=4)
    wprice_e = tk.Entry(win); wprice_e.pack(fill=tk.X, padx=10); wprice_e.insert(0, str(wprice0))

    tk.Label(win, text="Количество в зале:").pack(anchor="w", padx=10, pady=4)
    hall_e = tk.Entry(win); hall_e.pack(fill=tk.X, padx=10); hall_e.insert(0, str(hall_qty0))

    tk.Label(win, text="Количество на складе:").pack(anchor="w", padx=10, pady=4)
    storage_e = tk.Entry(win); storage_e.pack(fill=tk.X, padx=10); storage_e.insert(0, str(storage_qty0))

    def save_changes():
        try:
            new_name = name_e.get().strip()
            if not new_name:
                raise ValueError("Введите название")

            cat_str = cat_cb.get()
            new_cat_id = int(cat_str.split(" - ")[0]) if cat_str else None

            new_price = float(price_e.get())
            new_wprice = float(wprice_e.get())
            new_hall = int(hall_e.get())
            new_storage = int(storage_e.get())

            if new_hall < 0 or new_storage < 0:
                raise ValueError("Количество не может быть отрицательным")

            cursor.execute("""
                UPDATE 69420products
                SET name = %s, category_id = %s, price = %s, 
                    quantity_hall = %s, quantity_storage = %s, wholesale_price = %s
                WHERE id = %s;
            """, (new_name, new_cat_id, new_price, new_hall, new_storage, new_wprice, pid))

            commit()
            messagebox.showinfo("Успех", "Товар обновлён")
            win.destroy()

            # Безопасное обновление таблицы
            if current_tree_ref[0] is not None:
                try:
                    load_products_tree(current_tree_ref[0])
                except tk.TclError:
                    pass  # таблица закрыта — игнорируем

        except ValueError as ve:
            messagebox.showerror("Ошибка", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            conn.rollback()

    tk.Button(win, text="Сохранить", command=save_changes).pack(pady=12)

def make_sale_action(products_tree, entry_qty, entry_date, seller_combo, products_tree_refresh=None):
    sel = products_tree.selection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите товар для продажи")
        return
    item = products_tree.item(sel[0])['values']
    product_id = item[0]  # ← правильное имя

    try:
        qty = int(entry_qty.get())
        if qty <= 0:
            raise ValueError("Количество должно быть > 0")

        # Проверяем остаток в зале
        cursor.execute("SELECT quantity_hall FROM 69420products WHERE id = %s;", (product_id,))
        res = cursor.fetchone()
        available = res[0] if res else 0
        if qty > available:
            raise ValueError(f"Недостаточно в главном зале. Осталось: {available}")

        # Дата и продавец
        date_str = entry_date.get().strip()
        sale_date = None
        if date_str:
            sale_date = datetime.strptime(date_str, "%Y-%m-%d").date()  # только дата

        seller = seller_combo.get()
        seller_id = int(seller.split(" - ")[0]) if seller else None

        # Вставка в sales
        if sale_date and seller_id:
            cursor.execute(
                "INSERT INTO 69420sales (product_id, quantity, sale_date, seller_id) VALUES (%s,%s,%s,%s);",
                (product_id, qty, sale_date, seller_id)
            )
        elif seller_id:
            cursor.execute(
                "INSERT INTO 69420sales (product_id, quantity, seller_id) VALUES (%s,%s,%s);",
                (product_id, qty, seller_id)
            )
        else:
            cursor.execute(
                "INSERT INTO 69420sales (product_id, quantity) VALUES (%s,%s);",
                (product_id, qty)
            )

        # Уменьшаем количество в зале
        cursor.execute("UPDATE 69420products SET quantity_hall = quantity_hall - %s WHERE id = %s", (qty, product_id))

        commit()

        if products_tree_refresh:
            load_products_tree(products_tree_refresh)

        entry_qty.delete(0, tk.END)
        entry_date.delete(0, tk.END)
        messagebox.showinfo("Успех", "Продажа оформлена")

    except ValueError as ve:
        messagebox.showerror("Ошибка", str(ve))
    except Exception as e:
        messagebox.showerror("Ошибка БД", str(e))
        conn.rollback()

def show_report_action():
    """
    Отчёт по продажам: по дням и товарам + итоги внизу
    """
    cursor.execute("""
        SELECT DATE(s.sale_date) AS date, p.name,
               SUM(s.quantity) AS sold,
               SUM(s.quantity * COALESCE(p.wholesale_price,0)) AS cost,
               SUM(s.quantity * p.price) AS revenue
        FROM 69420sales s
        JOIN 69420products p ON s.product_id = p.id
        GROUP BY DATE(s.sale_date), p.name
        ORDER BY DATE(s.sale_date) ASC;
    """)
    rows = cursor.fetchall()
    if not rows:
        messagebox.showinfo("Отчёт", "Нет данных по продажам")
        return

    # Подсчёт общих итогов
    total_sold = sum(r[2] for r in rows)
    total_cost = sum(float(r[3] or 0) for r in rows)
    total_revenue = sum(float(r[4] or 0) for r in rows)
    total_profit = total_revenue - total_cost

    txt_lines = []
    for r in rows:
        date, name, sold, cost, revenue = r
        cost = float(cost or 0)
        revenue = float(revenue or 0)
        profit = revenue - cost
        txt_lines.append(f"{date} | {name} | Продано: {sold} | Себестоимость: {cost:.2f} | Выручка: {revenue:.2f} | Прибыль: {profit:.2f}")

    # Добавляем итоговую строку
    txt_lines.append("\n" + "="*80)
    txt_lines.append(f"ИТОГО: Продано {total_sold} шт. | Себестоимость: {total_cost:.2f} | Выручка: {total_revenue:.2f} | Прибыль: {total_profit:.2f}")

    txt = "\n".join(txt_lines)
    messagebox.showinfo("Отчёт по продажам (все время)", txt)

def show_report_period_action(date_from_entry, date_to_entry):
    try:
        df = date_from_entry.get().strip()
        dt = date_to_entry.get().strip()
        if not df or not dt:
            messagebox.showwarning("Внимание", "Введите обе даты")
            return

        cursor.execute("""
            SELECT DATE(s.sale_date) AS date, p.name,
                   SUM(s.quantity) AS sold,
                   SUM(s.quantity * COALESCE(p.wholesale_price,0)) AS cost,
                   SUM(s.quantity * p.price) AS revenue
            FROM 69420sales s JOIN 69420products p ON s.product_id = p.id
            WHERE DATE(s.sale_date) BETWEEN %s AND %s
            GROUP BY DATE(s.sale_date), p.name
            ORDER BY DATE(s.sale_date) ASC;
        """, (df, dt))
        rows = cursor.fetchall()
        if not rows:
            messagebox.showinfo("Отчёт", "Продаж за период нет")
            return

        total_sold = sum(r[2] for r in rows)
        total_cost = sum(float(r[3] or 0) for r in rows)
        total_revenue = sum(float(r[4] or 0) for r in rows)
        total_profit = total_revenue - total_cost

        lines = []
        for r in rows:
            date = r[0]
            name = r[1]
            sold = r[2] or 0
            cost = float(r[3] or 0)
            revenue = float(r[4] or 0)
            profit = revenue - cost
            lines.append(f"{date} | {name} | Продано: {sold} | Себестоимость: {cost:.2f} | Выручка: {revenue:.2f} | Прибыль: {profit:.2f}")

        lines.append("\n" + "="*80)
        lines.append(f"ИТОГО за период: Продано {total_sold} шт. | Себестоимость: {total_cost:.2f} | Выручка: {total_revenue:.2f} | Прибыль: {total_profit:.2f}")

        txt = "\n".join(lines)
        messagebox.showinfo(f"Отчёт {df} — {dt}", txt)
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def show_daily_summary_action():
    try:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(s.quantity * COALESCE(p.wholesale_price,0)),0) AS total_cost,
                COALESCE(SUM(s.quantity * p.price),0) AS total_revenue,
                COALESCE(SUM(s.quantity),0) AS total_sold
            FROM 69420sales s
            JOIN 69420products p ON s.product_id = p.id
            WHERE DATE(s.sale_date) = CURDATE();
        """)
        r = cursor.fetchone()
        total_cost = float(r[0] or 0)
        total_revenue = float(r[1] or 0)
        total_sold = int(r[2] or 0)
        profit = total_revenue - total_cost
        messagebox.showinfo("Итоги за день",
                            f"Продано товаров: {total_sold} шт.\n"
                            f"Выручка: {total_revenue:.2f} руб.\n"
                            f"Себестоимость: {total_cost:.2f} руб.\n"
                            f"Прибыль: {profit:.2f} руб.")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def show_top_product_action():
    try:
        cursor.execute("""
            SELECT p.name, SUM(s.quantity) AS total_sold
            FROM 69420sales s JOIN 69420products p ON s.product_id = p.id
            GROUP BY p.name
            ORDER BY total_sold DESC
            LIMIT 1;
        """)
        r = cursor.fetchone()
        if r:
            messagebox.showinfo("Популярный товар", f"{r[0]} — продано: {r[1]} шт")
        else:
            messagebox.showinfo("Популярный товар", "Нет данных")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def save_report_to_file_action():
    cursor.execute("""
        SELECT DATE(s.sale_date) AS date, p.name,
               SUM(s.quantity) AS sold,
               SUM(s.quantity * COALESCE(p.wholesale_price,0)) AS cost,
               SUM(s.quantity * p.price) AS revenue,
               se.name
        FROM 69420sales s
        JOIN 69420products p ON s.product_id = p.id
        LEFT JOIN 69420sellers se ON s.seller_id = se.id
        GROUP BY p.name, DATE(s.sale_date), se.name
        ORDER BY DATE(s.sale_date);
    """)
    rows = cursor.fetchall()
    if not rows:
        messagebox.showinfo("Отчёт", "Нет данных")
        return

    total_sold = sum(r[2] for r in rows)
    total_cost = sum(float(r[3] or 0) for r in rows)
    total_revenue = sum(float(r[4] or 0) for r in rows)
    total_profit = total_revenue - total_cost

    lines = ["ОТЧЁТ ПО ПРОДАЖАМ\n"]
    for r in rows:
        date, name, sold, cost, revenue, seller = r
        cost = float(cost or 0)
        revenue = float(revenue or 0)
        profit = revenue - cost
        lines.append(f"{date} | {name} | Продано: {sold} | Себестоимость: {cost:.2f} | Выручка: {revenue:.2f} | Прибыль: {profit:.2f} | Продавец: {seller or '—'}")

    lines.append("\n" + "="*90)
    lines.append(f"ИТОГО: Продано {total_sold} шт. | Себестоимость: {total_cost:.2f} | Выручка: {total_revenue:.2f} | Прибыль: {total_profit:.2f}")

    text = "\n".join(lines)
    path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("Успех", f"Отчёт сохранён: {path}")

def load_sellers_combo(combo):
    cursor.execute("SELECT id, name FROM 69420sellers;")
    s = cursor.fetchall()
    combo['values'] = [f"{r[0]} - {r[1]}" for r in s]

# -------------------------
# Новые/сохранённые функции: поставщики, склады, перемещения, покупки
# -------------------------
def show_suppliers_action():
    clear_workspace()
    lbl = tk.Label(right_frame, text="Поставщики", font=("Arial", 14, "bold"))
    lbl.pack(pady=5)
    cols = ("Номер", "Название", "Контакт")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    refresh_treeview(tree, "SELECT id, name, contact FROM 69420suppliers;")

    frm = tk.Frame(right_frame)
    frm.pack(pady=5)
    name_e = tk.Entry(frm); name_e.grid(row=0, column=0); name_e.insert(0, "Название")
    contact_e = tk.Entry(frm); contact_e.grid(row=0, column=1); contact_e.insert(0, "Контакт")

    def add_sup():
        n = name_e.get().strip(); c = contact_e.get().strip()
        if not n: messagebox.showwarning("Внимание", "Введите название"); return
        try:
            cursor.execute("INSERT INTO 69420suppliers (name, contact) VALUES (%s,%s);", (n,c))
            commit(); refresh_treeview(tree, "SELECT id, name, contact FROM 69420suppliers;")
            name_e.delete(0, tk.END); contact_e.delete(0, tk.END)
            messagebox.showinfo("OK", "Поставщик добавлен")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def del_sup():
        sel = tree.selection()
        if not sel: messagebox.showwarning("Внимание", "Выберите поставщика"); return
        pid = tree.item(sel[0])['values'][0]
        if not messagebox.askyesno("Подтвердить", "Удалить поставщика?"): return
        try:
            cursor.execute("DELETE FROM 69420suppliers WHERE id = %s;", (pid,))
            commit(); refresh_treeview(tree, "SELECT id, name, contact FROM 69420suppliers;")
            messagebox.showinfo("OK", "Удалено")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(frm, text="Добавить", command=add_sup).grid(row=0, column=2, padx=5)
    tk.Button(frm, text="Удалить", command=del_sup).grid(row=0, column=3, padx=5)

def show_sellers_action():
    """Панель управления продавцами"""
    clear_workspace()
    tk.Label(right_frame, text="Продавцы", font=("Arial", 14, "bold")).pack(pady=5)

    cols = ("Номер", "Имя продавца")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center")
    tree.column("Номер", width=80)
    tree.column("Имя продавца", width=200)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    refresh_treeview(tree, "SELECT id, name FROM 69420sellers ORDER BY id;")

    # Форма добавления
    frm = tk.Frame(right_frame)
    frm.pack(pady=10)

    tk.Label(frm, text="Имя продавца:").grid(row=0, column=0, padx=5)
    name_e = tk.Entry(frm, width=30)
    name_e.grid(row=0, column=1, padx=5)

    def add_seller():
        name = name_e.get().strip()
        if not name:
            messagebox.showwarning("Внимание", "Введите имя продавца!")
            return
        try:
            cursor.execute("INSERT INTO 69420sellers (name) VALUES (%s);", (name,))
            commit()
            refresh_treeview(tree, "SELECT id, name FROM 69420sellers ORDER BY id;")
            name_e.delete(0, tk.END)
            messagebox.showinfo("Успех", f"Продавец '{name}' добавлен")
        except mysql.connector.IntegrityError:
            messagebox.showerror("Ошибка", "Продавец с таким именем уже существует")
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

    def delete_seller():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите продавца для удаления")
            return
        seller_id, seller_name = tree.item(sel[0])["values"]
        if not messagebox.askyesno("Подтверждение", f"Удалить продавца '{seller_name}'?\nВсе его продажи останутся без указания продавца."):
            return
        try:
            cursor.execute("DELETE FROM 69420sellers WHERE id = %s;", (seller_id,))
            commit()
            refresh_treeview(tree, "SELECT id, name FROM 69420sellers ORDER BY id;")
            messagebox.showinfo("Успех", "Продавец удалён")
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))

    tk.Button(frm, text="Добавить", command=add_seller).grid(row=0, column=2, padx=10)
    tk.Button(right_frame, text="Удалить выбранного", command=delete_seller).pack(pady=5)

def show_warehouses_action():
    clear_workspace()
    tk.Label(right_frame, text="Склады и залы", font=("Arial", 14, "bold")).pack(pady=5)
    cols = ("Номер", "Название", "Тип")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols: tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    refresh_treeview(tree, "SELECT id, name, type FROM 69420warehouses;")

    frm = tk.Frame(right_frame); frm.pack(pady=5)
    name_e = tk.Entry(frm); name_e.grid(row=0, column=0); name_e.insert(0, "Название")
    type_cb = ttk.Combobox(frm, values=["основной зал", "склад"], state="readonly"); type_cb.grid(row=0, column=1)
    type_cb.set("склад")

    def add_wh():
        n = name_e.get().strip(); t = type_cb.get().strip()
        if not n: messagebox.showwarning("Внимание", "Введите название"); return
        try:
            cursor.execute("INSERT INTO 69420warehouses (name, type) VALUES (%s,%s);", (n,t))
            commit(); refresh_treeview(tree, "SELECT id, name, type FROM 69420warehouses;")
            name_e.delete(0, tk.END); type_cb.set("склад")
            messagebox.showinfo("OK", "Добавлено")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def del_wh():
        sel = tree.selection()
        if not sel: messagebox.showwarning("Внимание", "Выберите склад"); return
        wid = tree.item(sel[0])['values'][0]
        if not messagebox.askyesno("Подтвердить", "Удалить склад?"): return
        try:
            cursor.execute("DELETE FROM 69420warehouses WHERE id = %s;", (wid,))
            commit(); refresh_treeview(tree, "SELECT id, name, type FROM 69420warehouses;")
            messagebox.showinfo("OK", "Удалено")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(frm, text="Добавить", command=add_wh).grid(row=0, column=2, padx=5)
    tk.Button(frm, text="Удалить", command=del_wh).grid(row=0, column=3, padx=5)

def transfer_goods_action():
    clear_workspace()
    tk.Label(right_frame, text="Перемещение товара", font=("Arial", 14, "bold")).pack(pady=5)
    frm = tk.Frame(right_frame)
    frm.pack(pady=10)

    tk.Label(frm, text="Товар:").grid(row=0, column=0)
    product_cb = ttk.Combobox(frm, state="readonly")
    product_cb.grid(row=0, column=1)
    cursor.execute("SELECT id, name FROM 69420products;")
    prods = cursor.fetchall()
    product_cb['values'] = [f"{p[0]} - {p[1]}" for p in prods]

    tk.Label(frm, text="Со склада:").grid(row=1, column=0)
    from_cb = ttk.Combobox(frm, state="readonly")
    from_cb.grid(row=1, column=1)
    cursor.execute("SELECT id, name FROM 69420warehouses;")
    whs = cursor.fetchall()
    from_cb['values'] = [f"{w[0]} - {w[1]}" for w in whs]

    tk.Label(frm, text="На склад:").grid(row=2, column=0)
    to_cb = ttk.Combobox(frm, state="readonly")
    to_cb.grid(row=2, column=1)
    to_cb['values'] = from_cb['values']

    tk.Label(frm, text="Количество:").grid(row=3, column=0)
    qty_e = tk.Entry(frm)
    qty_e.grid(row=3, column=1)

    def do_transfer():
        try:
            pid_str = product_cb.get()
            from_str = from_cb.get()
            to_str = to_cb.get()
            qty_str = qty_e.get().strip()

            if not pid_str or not from_str or not to_str or not qty_str:
                messagebox.showwarning("Внимание", "Заполните все поля!")
                return

            pid = int(pid_str.split(" - ")[0])
            from_id = int(from_str.split(" - ")[0])
            to_id = int(to_str.split(" - ")[0])
            qty = int(qty_str)

            if qty <= 0:
                messagebox.showwarning("Внимание", "Количество должно быть больше 0")
                return

            if from_id == to_id:
                messagebox.showwarning("Внимание", "Склад отправитель и получатель не могут быть одинаковыми")
                return

            # Проверяем наличие товара
            cursor.execute("SELECT quantity_hall, quantity_storage FROM 69420products WHERE id = %s", (pid,))
            hall, storage = cursor.fetchone()

            main_hall = get_main_hall_id()

            if from_id == main_hall:
                if hall < qty:
                    messagebox.showerror("Ошибка", "Недостаточно товара в зале")
                    return
            else:
                if storage < qty:
                    messagebox.showerror("Ошибка", "Недостаточно товара на складе")
                    return

            # Обновляем остатки напрямую
            if from_id == main_hall:
                cursor.execute("UPDATE 69420products SET quantity_hall = quantity_hall - %s, quantity_storage = quantity_storage + %s WHERE id = %s",
                               (qty, qty, pid))
            else:
                cursor.execute("UPDATE 69420products SET quantity_hall = quantity_hall + %s, quantity_storage = quantity_storage - %s WHERE id = %s",
                               (qty, qty, pid))

            commit()
            messagebox.showinfo("Успех", "Товар перемещён!")
            if current_tree_ref[0] is not None and current_tree_ref[0].winfo_exists():
                load_products_tree(current_tree_ref[0])

        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат данных (количество должно быть числом)")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            conn.rollback()

    tk.Button(frm, text="Переместить", command=do_transfer).grid(row=4, column=0, columnspan=2, pady=8)
def categories_panel():
    clear_workspace()
    tk.Label(right_frame, text="Категории товаров", font=("Arial", 14, "bold")).pack(pady=5)

    cols = ("ID", "Название")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def refresh():
        refresh_treeview(tree, "SELECT id, name FROM 69420categories")

    refresh()

    # ------------------------------
    # Блок добавления категории
    # ------------------------------
    frm_add = tk.Frame(right_frame)
    frm_add.pack(pady=10)

    tk.Label(frm_add, text="Название категории:").grid(row=0, column=0)
    name_e = tk.Entry(frm_add)
    name_e.grid(row=0, column=1)

    def add_cat():
        n = name_e.get().strip()
        if not n:
            messagebox.showwarning("Внимание", "Введите название категории")
            return
        try:
            cursor.execute("INSERT INTO 69420categories (name) VALUES (%s)", (n,))
            commit()
            refresh()
            name_e.delete(0, tk.END)
            messagebox.showinfo("OK", "Категория добавлена")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(frm_add, text="Добавить", command=add_cat).grid(row=0, column=2, padx=5)

    # ------------------------------
    # Удаление категории
    # ------------------------------
    def delete_cat():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите категорию")
            return
        cid, cname = tree.item(sel[0])["values"]
        if not messagebox.askyesno("Подтвердить", f"Удалить категорию '{cname}'?"):
            return

        try:
            # Запрещено удалять, если в категории есть товары
            cursor.execute("SELECT COUNT(*) FROM 69420products WHERE category_id=%s", (cid,))
            if cursor.fetchone()[0] > 0:
                messagebox.showerror("Ошибка", "Нельзя удалить категорию — есть товары!")
                return

            cursor.execute("DELETE FROM 69420categories WHERE id=%s", (cid,))
            commit()
            refresh()
            messagebox.showinfo("OK", "Удалено")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    tk.Button(right_frame, text="Удалить выбранную", command=delete_cat).pack(pady=5)

    # ------------------------------
    # Редактирование категории
    # ------------------------------
    def edit_cat():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите категорию")
            return

        cid, cname = tree.item(sel[0])["values"]

        win = tk.Toplevel(root)
        win.title("Редактировать категорию")
        win.geometry("300x150")

        tk.Label(win, text="Новое название:").pack(pady=5)
        e = tk.Entry(win)
        e.pack(fill=tk.X, padx=10)
        e.insert(0, cname)

        def save():
            new_name = e.get().strip()
            if not new_name:
                messagebox.showwarning("Внимание", "Введите название")
                return
            try:
                cursor.execute("UPDATE 69420categories SET name=%s WHERE id=%s", (new_name, cid))
                commit()
                refresh()
                win.destroy()
                messagebox.showinfo("OK", "Обновлено")
            except Exception as ex:
                messagebox.showerror("Ошибка", str(ex))

        tk.Button(win, text="Сохранить", command=save).pack(pady=10)

    tk.Button(right_frame, text="Редактировать выбранную", command=edit_cat).pack(pady=5)


def receive_from_supplier_action():
    clear_workspace()
    tk.Label(right_frame, text="Приём товара от поставщика", font=("Arial", 14, "bold")).pack(pady=5)
    frm = tk.Frame(right_frame)
    frm.pack(pady=10)

    tk.Label(frm, text="Поставщик:").grid(row=0, column=0)
    sup_cb = ttk.Combobox(frm, state="readonly")
    sup_cb.grid(row=0, column=1)
    cursor.execute("SELECT id, name FROM 69420suppliers;")
    sup_cb['values'] = [f"{r[0]} - {r[1]}" for r in cursor.fetchall()]

    tk.Label(frm, text="Товар:").grid(row=1, column=0)
    prod_cb = ttk.Combobox(frm, state="readonly")
    prod_cb.grid(row=1, column=1)
    cursor.execute("SELECT id, name FROM 69420products;")
    prod_cb['values'] = [f"{r[0]} - {r[1]}" for r in cursor.fetchall()]

    tk.Label(frm, text="В склад:").grid(row=2, column=0)
    to_cb = ttk.Combobox(frm, state="readonly")
    to_cb.grid(row=2, column=1)
    cursor.execute("SELECT id, name FROM 69420warehouses;")
    to_cb['values'] = [f"{r[0]} - {r[1]}" for r in cursor.fetchall()]

    tk.Label(frm, text="Количество:").grid(row=3, column=0)
    qty_e = tk.Entry(frm)
    qty_e.grid(row=3, column=1)

    # Новое поле - цена закупки
    tk.Label(frm, text="Цена закупки:").grid(row=4, column=0)
    purchase_price_e = tk.Entry(frm)
    purchase_price_e.grid(row=4, column=1)

    def receive():
        try:
            sup = sup_cb.get()
            prod = prod_cb.get()
            to = to_cb.get()
            if not prod or not to or not sup:
                raise ValueError("Выберите поставщика, товар и склад")
            pid = int(prod.split(" - ")[0])
            to_id = int(to.split(" - ")[0])
            sup_id = int(sup.split(" - ")[0])
            qty = int(qty_e.get())
            if qty <= 0:
                raise ValueError("Кол-во > 0")
            purchase_price = float(purchase_price_e.get())

            # Запись в purchases (сохраняем учёт закупок)
            cursor.execute("""
                INSERT INTO 69420purchases (product_id, supplier_id, warehouse_id, quantity, purchase_price)
                VALUES (%s, %s, %s, %s, %s);
            """, (pid, sup_id, to_id, qty, purchase_price))

            # Обновляем остаток напрямую
            main_hall_id = get_main_hall_id()
            if to_id == main_hall_id:
                cursor.execute("UPDATE 69420products SET quantity_hall = quantity_hall + %s WHERE id = %s", (qty, pid))
            else:
                cursor.execute("UPDATE 69420products SET quantity_storage = quantity_storage + %s WHERE id = %s", (qty, pid))

            # Обновляем закупочную цену
            cursor.execute("UPDATE 69420products SET wholesale_price = %s WHERE id = %s", (purchase_price, pid))

            commit()
            messagebox.showinfo("OK", "Приём зарегистрирован")
            if current_tree_ref[0] is not None and current_tree_ref[0].winfo_exists():
                load_products_tree(current_tree_ref[0])

        except ValueError as ve:
            messagebox.showerror("Ошибка", str(ve))
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            conn.rollback()

    tk.Button(frm, text="Принять", command=receive).grid(row=5, column=0, columnspan=2, pady=8)

def show_purchases_history():
    clear_workspace()
    tk.Label(right_frame, text="История закупок", font=("Arial", 14, "bold")).pack(pady=5)

    # Новые колонки с точными ширинами — последний столбец теперь шире и видно полностью
    cols = ("Дата", "Товар", "Поставщик", "Склад", "Кол-во", "Цена закупки", "Сумма")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")

    # Задаём ширину каждого столбца вручную — проверено, всё помещается
    tree.column("Дата",         width=90,   anchor="center")
    tree.column("Товар",        width=220,  anchor="w")
    tree.column("Поставщик",    width=140,  anchor="w")
    tree.column("Склад",        width=120,  anchor="w")
    tree.column("Кол-во",       width=70,   anchor="center")
    tree.column("Цена закупки", width=110,  anchor="e")
    tree.column("Сумма",        width=140,  anchor="e")   # ← самый важный, теперь 140 — всегда видно 12345.67

    for c in cols:
        tree.heading(c, text=c)

    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Запрос остаётся тот же
    cursor.execute("""
        SELECT DATE(purchase_date) AS dt, pr.name, s.name, w.name,
               p.quantity, p.purchase_price, (p.quantity * p.purchase_price) AS total
        FROM 69420purchases p
        JOIN 69420products pr ON p.product_id = pr.id
        LEFT JOIN 69420suppliers s ON p.supplier_id = s.id
        LEFT JOIN 69420warehouses w ON p.warehouse_id = w.id
        ORDER BY p.purchase_date DESC;
    """)

    for row in cursor.fetchall():
        # Форматируем сумму сразу с двумя знаками — выглядит красиво
        formatted_row = list(row)
        formatted_row[6] = f"{formatted_row[6]:,.2f}" if formatted_row[6] is not None else "0.00"
        tree.insert("", tk.END, values=formatted_row)

# -------------------------
# GUI: левое меню + правое рабочее поле
# -------------------------
root = tk.Tk()
root.title("Магазин канцтоваров — Панель управления")
root.geometry("1200x800")

menu_frame = tk.Frame(root, bg="#2f4f6f", width=260)
menu_frame.pack(side=tk.LEFT, fill=tk.Y)

right_frame = tk.Frame(root, bg="#f5f7fa")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# --- ВАЖНО: ссылка на текущее treeview (используется в edit_product_action) ---
current_tree_ref = [None]

def main_btn(text):
    return tk.Button(menu_frame, text=text, anchor="w", padx=10, pady=8,
                     bg="#3b5f82", fg="white", relief="flat", font=("Arial", 11, "bold"))

# Список (frame, button) всех категорий — используем, чтобы сворачивать другие
category_widgets = []

def toggle_frame(active_frame, associated_btn=None, prep=None):
    """
    Открывает выбранный фрейм и закрывает остальные.
    При открытии размещает active_frame сразу под associated_btn.
    """
    # Скрываем все остальные
    for f, b in category_widgets:
        if f is not active_frame and f.winfo_ismapped():
            f.pack_forget()

    # Если уже открыт — закрываем
    if active_frame.winfo_ismapped():
        active_frame.pack_forget()
        return

    # Если есть подготовка — выполнить (наполнение кнопок и т.д.)
    if prep:
        prep()

    # Размещаем frame сразу под соответствующей кнопкой (after=associated_btn)
    # если associated_btn предоставлен — используем его, иначе просто pack
    if associated_btn:
        # pack with after to place right below the button
        active_frame.pack(fill=tk.X, padx=6, pady=2, after=associated_btn)
    else:
        active_frame.pack(fill=tk.X, padx=6, pady=2)

# -- Блок Товары (с подменю) --
btn_goods = main_btn("📦 Товары")
btn_goods.pack(fill=tk.X, pady=(10,0))
frame_goods = tk.Frame(menu_frame, bg="#355d7a")
category_widgets.append((frame_goods, btn_goods))

def add_goods_buttons():
    for w in frame_goods.winfo_children(): w.destroy()
    tk.Button(frame_goods, text="Все товары", anchor="w", bg="#355d7a", fg="white",
              command=lambda: show_products_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_goods, text="Товары в зале", anchor="w", bg="#355d7a", fg="white",
              command=lambda: show_products_hall_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_goods, text="Товары на складе", anchor="w", bg="#355d7a", fg="white",
              command=lambda: show_storage_products_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_goods, text="Добавить товар", anchor="w", bg="#355d7a", fg="white",
              command=lambda: add_product_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_goods, text="Удалить товар", anchor="w", bg="#355d7a", fg="white",
              command=lambda: delete_product_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_goods, text="Категории", anchor="w", bg="#355d7a", fg="white",
              command=lambda: categories_panel()).pack(fill=tk.X, padx=20, pady=2)

btn_goods.config(command=lambda: toggle_frame(frame_goods, associated_btn=btn_goods, prep=add_goods_buttons))

# -- Блок Продажи --
btn_sales = main_btn("💰 Продажи")
btn_sales.pack(fill=tk.X, pady=(8,0))
frame_sales = tk.Frame(menu_frame, bg="#355d7a")
category_widgets.append((frame_sales, btn_sales))


def add_sales_buttons():
    for w in frame_sales.winfo_children(): w.destroy()
    tk.Button(frame_sales, text="Оформить продажу", anchor="w", bg="#355d7a", fg="white",
              command=lambda: sell_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_sales, text="Просмотр продаж", anchor="w", bg="#355d7a", fg="white",
              command=lambda: show_sales_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_sales, text="Продавцы", anchor="w", bg="#355d7a", fg="white",
              command=show_sellers_action).pack(fill=tk.X, padx=20, pady=2)

btn_sales.config(command=lambda: toggle_frame(frame_sales, associated_btn=btn_sales, prep=add_sales_buttons))

# -- Блок Склады/Поставки --
btn_wh = main_btn("🏬 Склады / Поставщики")
btn_wh.pack(fill=tk.X, pady=(8,0))
frame_wh = tk.Frame(menu_frame, bg="#355d7a")
category_widgets.append((frame_wh, btn_wh))

def add_wh_buttons():
    for w in frame_wh.winfo_children(): w.destroy()
    tk.Button(frame_wh, text="Показать склады", anchor="w", bg="#355d7a", fg="white",
              command=show_warehouses_action).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_wh, text="Перемещение (с интерфейсом)", anchor="w", bg="#355d7a", fg="white",
              command=transfer_goods_action).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_wh, text="Поставщики", anchor="w", bg="#355d7a", fg="white",
              command=show_suppliers_action).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_wh, text="История закупок", anchor="w", bg="#355d7a", fg="white",
              command=show_purchases_history).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_wh, text="Приём от поставщика", anchor="w", bg="#355d7a", fg="white",
              command=receive_from_supplier_action).pack(fill=tk.X, padx=20, pady=2)

btn_wh.config(command=lambda: toggle_frame(frame_wh, associated_btn=btn_wh, prep=add_wh_buttons))

# -- Блок Отчёты --
btn_reports = main_btn("📊 Отчёты")
btn_reports.pack(fill=tk.X, pady=(8,0))
frame_reports = tk.Frame(menu_frame, bg="#355d7a")
category_widgets.append((frame_reports, btn_reports))

def add_reports_buttons():
    for w in frame_reports.winfo_children(): w.destroy()
    tk.Button(frame_reports, text="Отчёт по продажам", anchor="w", bg="#355d7a", fg="white",
              command=show_report_action).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_reports, text="Отчёт за период", anchor="w", bg="#355d7a", fg="white",
              command=lambda: report_period_panel()).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_reports, text="Итоги за день", anchor="w", bg="#355d7a", fg="white",
              command=show_daily_summary_action).pack(fill=tk.X, padx=20, pady=2)
    tk.Button(frame_reports, text="Сохранить отчёт .txt", anchor="w", bg="#355d7a", fg="white",
              command=save_report_to_file_action).pack(fill=tk.X, padx=20, pady=2)

btn_reports.config(command=lambda: toggle_frame(frame_reports, associated_btn=btn_reports, prep=add_reports_buttons))

# -------------------------
# Панели (реализация экранов)
# -------------------------
def show_products_panel():
    clear_workspace()
    tk.Label(right_frame, text="Все товары", font=("Arial", 14, "bold")).pack(pady=5)
    cols = ("Артикул", "Название", "Категория", "Цена", "Кол-во (зал)", "Кол-во (склад)", "Итого")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        if c == "Название":
            tree.column(c, width=220)
        elif c == "Категория":
            tree.column(c, width=150)
        elif c == "Цена":
            tree.column(c, width=80, anchor="center")
        elif c == "Кол-во (зал)":
            tree.column(c, width=100, anchor="center")
        elif c == "Кол-во (склад)":
            tree.column(c, width=110, anchor="center")
        elif c == "Итого":
            tree.column(c, width=100, anchor="center")

    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    # сохраним ссылку на текущее дерево для обновления после редактирования
    current_tree_ref[0] = tree
    load_products_tree(tree)

    frm = tk.Frame(right_frame); frm.pack(pady=6)
    tk.Button(frm, text="Редактировать выбранный", command=lambda: edit_product_action(tree)).pack(side=tk.LEFT, padx=6)
    tk.Button(frm, text="Удалить выбранный", command=lambda: delete_product_action(tree)).pack(side=tk.LEFT, padx=6)

def show_products_hall_panel():
    clear_workspace()
    tk.Label(right_frame, text="Товары в зале", font=("Arial", 14, "bold")).pack(pady=5)
    cols = ("Артикул", "Название", "Категория", "Цена", "Кол-во (зал)")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols: tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    current_tree_ref[0] = tree
    load_products_tree(tree, only_hall=True)

    frm = tk.Frame(right_frame); frm.pack(pady=6)
    tk.Button(frm, text="Редактировать выбранный", command=lambda: edit_product_action(tree)).pack(side=tk.LEFT, padx=6)

def show_storage_products_panel():
    clear_workspace()
    tk.Label(right_frame, text="Товары на складе",
             font=("Arial", 14, "bold")).pack(pady=5)

    cols = ("Артикул", "Название", "Категория", "Цена", "Кол-во(склад)")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    load_products_tree(tree, only_storage=True)

def add_product_panel():
    clear_workspace()
    tk.Label(right_frame, text="Добавить товар", font=("Arial", 14, "bold")).pack(pady=5)
    frm = tk.Frame(right_frame); frm.pack(pady=10)
    tk.Label(frm, text="Название:").grid(row=0,column=0); name_e = tk.Entry(frm); name_e.grid(row=0,column=1)
    tk.Label(frm, text="Категория:").grid(row=1,column=0); cat_cb = ttk.Combobox(frm, state="readonly"); cat_cb.grid(row=1,column=1)
    load_categories_combo(cat_cb)
    tk.Label(frm, text="Цена:").grid(row=2,column=0); price_e = tk.Entry(frm); price_e.grid(row=2,column=1)
    tk.Label(frm, text="Кол-во в зале:").grid(row=3,column=0); qty_e = tk.Entry(frm); qty_e.grid(row=3,column=1)
    tk.Label(frm, text="Закупочная цена:").grid(row=4,column=0); wprice_e = tk.Entry(frm); wprice_e.grid(row=4,column=1)

    # Правильный способ — обновляем главную таблицу через current_tree_ref
    def add_and_refresh():
        add_product_action(name_e, cat_cb, price_e, qty_e, wprice_e)
        # После добавления обновляем текущую открытую таблицу товаров, если она есть
        if current_tree_ref[0] is not None and current_tree_ref[0].winfo_exists():
            load_products_tree(current_tree_ref[0])

    tk.Button(right_frame, text="Добавить", command=add_and_refresh).pack(pady=12)

def delete_product_panel():
    clear_workspace()
    tk.Label(right_frame, text="Удалить товар", font=("Arial", 14, "bold")).pack(pady=5)
    cols = ("Артикул", "Название", "Цена", "Кол-во (зал)")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols: tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    refresh_treeview(tree, "SELECT id, name, price, quantity_hall FROM 69420products;")
    tk.Button(right_frame, text="Удалить выбранный", command=lambda: delete_product_action(tree)).pack(pady=6)

def sell_panel():
    clear_workspace()
    tk.Label(right_frame, text="Оформление продажи", font=("Arial", 14, "bold")).pack(pady=5)

    # Всегда одинаковые колонки: ID, Название, Категория, Цена, Кол-во
    cols = ("Артикул", "Название", "Категория", "Цена", "Кол-во в зале")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # Загружаем товары через load_products_tree, чтобы порядок колонок не ломался
    load_products_tree(tree, only_hall=True)

    frm = tk.Frame(right_frame); frm.pack(pady=8)
    tk.Label(frm, text="Кол-во:").grid(row=0, column=0)
    qty_e = tk.Entry(frm); qty_e.grid(row=0, column=1)

    tk.Label(frm, text="Дата (YYYY-MM-DD):").grid(row=1, column=0)
    date_e = tk.Entry(frm); date_e.grid(row=1, column=1)

    tk.Label(frm, text="Продавец:").grid(row=2, column=0)
    seller_cb = ttk.Combobox(frm, state="readonly"); seller_cb.grid(row=2, column=1)
    load_sellers_combo(seller_cb)

    # Передаем тот же Treeview для обновления после продажи
    tk.Button(right_frame, text="Продать",
              command=lambda: make_sale_action(tree, qty_e, date_e, seller_cb, products_tree_refresh=tree)
             ).pack(pady=6)

def show_sales_panel():
    clear_workspace()
    tk.Label(right_frame, text="Список продаж", font=("Arial", 14, "bold")).pack(pady=5)
    cols = ("Дата","Товар","Кол-во","Выручка","Продавец")
    tree = ttk.Treeview(right_frame, columns=cols, show="headings")
    for c in cols: tree.heading(c, text=c)
    tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    query = """
        SELECT DATE(s.sale_date), p.name, s.quantity, s.quantity * p.price, se.name
        FROM 69420sales s
        LEFT JOIN 69420products p ON s.product_id = p.id
        LEFT JOIN 69420sellers se ON s.seller_id = se.id
        ORDER BY s.sale_date DESC;
    """
    refresh_treeview(tree, query)

def report_period_panel():
    clear_workspace()
    tk.Label(right_frame, text="Отчёт за период", font=("Arial", 14, "bold")).pack(pady=5)
    frm = tk.Frame(right_frame); frm.pack(pady=10)
    tk.Label(frm, text="с (YYYY-MM-DD):").grid(row=0,column=0); df = tk.Entry(frm); df.grid(row=0,column=1)
    tk.Label(frm, text="по (YYYY-MM-DD):").grid(row=1,column=0); dt = tk.Entry(frm); dt.grid(row=1,column=1)
    tk.Button(right_frame, text="Показать", command=lambda: show_report_period_action(df, dt)).pack(pady=6)

# -------------------------
# Инициализация: показать панель товаров по умолчанию
# -------------------------
show_products_panel()

# старт GUI
root.mainloop()

# закрытие соединения
cursor.close()
conn.close()
