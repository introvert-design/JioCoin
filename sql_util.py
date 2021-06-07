from app import mysql


class Table:
    def __init__(self, table_name, *args):
        self.table_name = table_name
        self.columns = args
        self.create_new_table()

    @staticmethod
    def sql_operations(operation, query):
        cur = mysql.connection.cursor()
        cur.execute(query)
        if operation == 'get_all':
            result = cur.fetchall()
        elif operation == 'get_one':
            result = cur.fetchone()
        else:
            mysql.connection.commit()
            result = True
        cur.close()
        return result

    def is_new_table(self):
        cur = mysql.connection.cursor()

        try:
            cur.execute(f'SELECT * FROM {self.table_name};')
            return False
        except Exception as e:
            x = e.args[0]
            if x == 1146:
                return True
            else:
                raise e
        finally:
            cur.close()

    def create_new_table(self):
        if self.is_new_table():
            column_headers = ', '.join([f'{column_name} varchar({size})' for column_name, size in self.columns])
            query = f'CREATE TABLE {self.table_name} ({column_headers});'
            self.sql_operations('create', query)

    def get_all_data(self):
        query = f'SELECT * FROM {self.table_name};'
        result = self.sql_operations('get_all', query)
        return result

    def get_one(self, search, value):
        query = f'SELECT * FROM {self.table_name} WHERE {search} = "{value}";'
        result = self.sql_operations('get_one', query)
        return result

    def insert_data(self, *args):
        values = ', '.join([f'"{arg}"' for arg in args])
        query = f'INSERT INTO {self.table_name} VALUES ({values});'
        self.sql_operations('insert', query)

    def delete_one(self, search, value):
        query = f'DELETE FROM {self.table_name} WHERE {search} = "{value}";'
        self.sql_operations('delete_one', query)

    def delete_all_data(self):
        query = f'DROP TABLE {self.table_name};'
        self.sql_operations('delete_all', query)
        self.create_new_table()

    def is_new_user(self, email):
        result = self.get_one('email', email)
        if result is None:
            return True
        else:
            return False
