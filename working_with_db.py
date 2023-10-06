import sqlite3 as sl
import datetime

def get_or_create_db(connection):
    table_name = 'messages'
    # открываем базу
    with connection:
        # получаем количество таблиц с нужным нам именем
        data = connection.execute(
            f"select count(*) from sqlite_master where type='table' and name='messages'")
        for row in data:
            # если таких таблиц нет
            if row[0] == 0:
                # создаём таблицу для товаров
                with connection:
                    connection.execute(f"""
                        CREATE TABLE {table_name} (
                            id INTEGER PRIMARY KEY,
                            tg_message_id INTEGER,
                            from_user_id INTEGER,
                            chat_id INTEGER,
                            from_user_first_name VARCHAR(40),
                            date INTEGER,
                            text VARCHAR(4000)
                        );
                    """)


def add_data_to_db(con, data: list):
    table_name = "messages"
    fields_name = '(tg_message_id, from_user_id, chat_id, from_user_first_name, date, text)'
    len_fields_name = 6

    values = "(" + ', '.join(["?" for x in range(len_fields_name)]) + ")"
    # подготавливаем множественный запрос
    sql = f'INSERT INTO {table_name} {fields_name} values{values}'
    # указываем данные для запроса

    # добавляем с помощью множественного запроса все данные сразу
    with con:
        con.executemany(sql, data)

def read_data_from_db(con):
    table_name = 'messages'
    # выводим содержимое таблицы на экран
    with con:
        result =[]
        data = con.execute(f"SELECT * FROM {table_name}")
        for row in data:
            result.append(row)

        return result

def read_message_from_db(con):
    table_name = 'messages'

    with con:
        result =[]
        data = con.execute(f"SELECT text FROM {table_name}")
        for row in data:
            result.append(row)

        return result



if __name__ == "__main__":

    now = datetime.datetime.now()
    delta = (now - datetime.datetime(1970, 1, 1))
    data = [
        (1124, 99076897, -4044068024, 'Ilya', delta.total_seconds(), 'привет'),
    ]

    con = sl.connect('db.db')



    get_or_create_db(con)
    add_data_to_db(con, data)
    read_data_from_db(con)