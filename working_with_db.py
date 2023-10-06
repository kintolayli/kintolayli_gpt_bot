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

def send_query_to_db(con, query):
    with con:
        result =[]
        data = con.execute(query)
        for row in data:
            result.append(row[0])

        return result

def select_all_messages_from_db_today(con, chat_id, table_name="messages"):
    query = f"""
        SELECT text FROM {table_name}
        WHERE date >= DATE('now', 'start of day') AND
        date < DATE('now', 'start of day', '+1 day')
        AND chat_id = {chat_id};
        """
    return send_query_to_db(con, query)

def select_all_messages_from_db_all_time(con, table_name="messages"):
    query = f"SELECT text FROM {table_name}"
    return send_query_to_db(con, query)

def select_all_data_from_db_all_time(con, table_name="messages"):
    query = f"SELECT * FROM {table_name}"
    return send_query_to_db(con, query)

def select_last_n_messages_from_db(con, count, chat_id, table_name="messages"):
    query = f"""
    SELECT text FROM {table_name}
    WHERE chat_id = {chat_id}
    ORDER BY date DESC
    LIMIT {count};
        """
    return send_query_to_db(con, query)


if __name__ == "__main__":
    date = datetime.datetime(year=2023, month=10, day=7, hour=10, minute=0, second=0)
    date = date.isoformat(sep=" ", timespec="seconds")

    data = [
        (1194, 99076897, -4044068024, 'Ilya', date, 'b: все'),
        (1195, 99076897, -4044068024, 'Ilya', date, 'b: сообщения'),
        (1196, 99076897, -4044068024, 'Ilya', date, 'b: c префиксом b'),
        (1197, 99076897, -4044068024, 'Ilya', date, 'b: из будущего'),
        (1198, 99076897, -4044068024, 'Ilya', date, 'b: и их не надо выбирать'),
        (1199, 99076897, -4044068024, 'Ilya', date, 'b: конец'),
    ]

    con = sl.connect('db.db')
    get_or_create_db(con)
    add_data_to_db(con, data)
    # select_all_data_from_db_all_time(con)