import mysql.connector as sql
from mysql.connector import Error

from config import _mysql_user, _mysql_password
from helper import is_json


class Table:
    """
    Checks whether the user is a new user.
    Executes the MySQL queries to-
        * Check the existence of a table.
        * Create a new table.
        * Get all the data from a table.
        * Get the data from specific rows in a table using search value.
        * Insert new data(row) into the table.
        * Delete specific data(rows) from the table.
        * Delete all the data from the table.
        * Update a row in the table with new values.
    """
    def __init__(self, table_name, mysql, *args):
        self.table_name = table_name
        self.mysql = mysql
        self.columns = args
        self.create_new_table()

    def sql_operations(self, operation, query):
        """
        Establishes connection with MySQL server and executes the MySQL query.
        :param operation: Operation to be performed on the MySQL database.
        :param query: MySQL query for different operations on MySQL database.
        :return: dictionary - a row as a dictionary to get data from a specific row.
                 a list of dictionaries - the rows as a list of dictionaries to get all the data from the table.
                 boolean - True: if operations execute successfully.
        """
        if self.table_name == 'users':
            cur = self.mysql.connection.cursor()
        else:
            cur = self.mysql.cursor(buffered=True, dictionary=True)
        cur.execute(query)
        if operation == 'get_all':
            result = cur.fetchall()
        elif operation == 'get_one':
            result = cur.fetchone()
        elif self.table_name == 'users':
            self.mysql.connection.commit()
            result = True
        else:
            self.mysql.commit()
            result = True
        cur.close()
        return result

    def is_new_table(self):
        """
        Checks whether a table is new.
        :return: boolean - True: if the table is new.
                           False: if the table already exists.
        """
        if self.table_name == 'users':
            cur = self.mysql.connection.cursor()
        else:
            cur = self.mysql.cursor(buffered=True)
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

    @staticmethod
    def create_db(db_name):
        """
        creates a database for the blockchain
        :return: boolean - True: if the database is created without any error.
                           False: if the database is not created because of any error.
        """
        conn = sql.connect(
            host='localhost',
            user=_mysql_user,
            password=_mysql_password
        )
        cur = conn.cursor()
        try:
            cur.execute(f"CREATE DATABASE {db_name}")
            return 1
        except Error as e:
            x = e.args[0]
            if x == 1007:
                return 1
            else:
                return 0
        finally:
            cur.close()

    def create_new_table(self):
        """
        Creates a new table if a table of the same name does not exists.
        :return: None.
        """
        if self.is_new_table():
            column_headers = ', '.join([f'{column_name} {data_type}'
                                        if data_type == 'JSON' or data_type == 'BOOL'
                                        else f'{column_name} {data_type}({size}) {constraint}'
                                        for column_name, data_type, size, constraint in self.columns])
            query = f'CREATE TABLE {self.table_name} ({column_headers}, PRIMARY KEY ({self.columns[0][0]}));'
            self.sql_operations('create', query)

    def get_all_data(self):
        """
        Get all the data or rows from a table.
        :return: a list of dictionaries - the rows as a list of dictionaries.
        """
        query = f'SELECT * FROM {self.table_name};'
        result = self.sql_operations('get_all', query)
        return result

    def get_one_column(self, column_name):
        """
        Get a column from the table.
        :return: a list of values under the column.
        """
        query = f'SELECT {column_name} FROM {self.table_name};'
        result = self.sql_operations('get_all', query)
        return result

    def get_one(self, search, value):
        """
        Gets the data from specific row or rows in a table using search value.
        :param search: The column header helps construct the condition to identify the specific row or relevant data.
        :param value: The value of the column to identify the specific row in the table.
        :return: dictionary - the row as a dictionary.
        """
        query = f'SELECT * FROM {self.table_name} WHERE {search} = "{value}";'
        result = self.sql_operations('get_one', query)
        return result

    def insert_data(self, *args):
        """
        Inserts new data(a new row) into the table.
        :param args: A list of values to be inserted as a new row to the table.
        :return: None.
        """
        values = ', '.join([f'"{arg}"' if not is_json(arg) else f"'{arg}'" for arg in args])
        query = f'INSERT INTO {self.table_name} VALUES ({values});'
        self.sql_operations('insert', query)

    def delete_one(self, search, value):
        """
        Delete specific data(rows) from the table.
        :param search: The column header helps construct the condition to identify the row to be deleted.
        :param value: The value of the column to identify the row to be deleted.
        :return: None.
        """
        query = f'DELETE FROM {self.table_name} WHERE {search} = "{value}";'
        self.sql_operations('delete_one', query)

    def delete_all_data(self):
        """
        Delete all the data from the table.
        :return: None.
        """
        query = f'DROP TABLE {self.table_name};'
        self.sql_operations('delete_all', query)
        self.create_new_table()

    def update_table(self, condition, *args):
        """
        Updates a row in the table with new values.
        :param condition: A tuple with column header and value helps construct the condition to identify
        the row to be updated.
        :param args: A list of tuples with column header and value pair. The current values under the column headers is
        updated with the provided values.
        :return: None.
        """
        columns_to_be_updated = ', '.join([f'{column_name} = "{value}"' for column_name, value in args])
        column, val = condition
        query = f'UPDATE {self.table_name} SET {columns_to_be_updated} WHERE {column} = "{val}";'
        self.sql_operations('update', query)

    def is_new_user(self, email):
        """
        Checks whether the user is new.
        :param email: The email of the user.
        :return: boolean - True: if the user is new.
                           False: if the user is not new.
        """
        result = self.get_one('email', email)
        if result is None:
            return True
        else:
            return False


def nodes(mysql, email):
    users = Table("users", mysql,
                  ("email", "VARCHAR", 50, "UNIQUE"),
                  ("name", "VARCHAR", 50, ""),
                  ("node", "VARCHAR", 80, "UNIQUE"),
                  ("password", "VARCHAR", 100, ""),
                  ("public_key", "VARCHAR", 2048, ""),
                  ("has_wallet", "BOOL", "", ""),
                  ("db_created", "BOOL", "", "")
                  )
    node_list = users.get_one_column('node')
    node_list = [node['node'] for node in node_list]
    user_node = users.get_one('email', email)
    node_list.remove(user_node['node'])
    return node_list
