'''
Manages all ToDoIt users including login and password reset functionality.
'''
from typing import *

import flask_login
import hashlib
import jwt
import sqlite3 as sql
import time
import uuid


class User(flask_login.UserMixin):
    '''Subclass of flask_login.UserMixin, also handles database user data.
    '''

    def __init__(self, username: str, database='todo_table.db') -> None:
        '''Initializes User object with username and database.

        Args:
            username: Username of user.
            database: Database where User data is stored, this argument should
                      be kept as the default except for class unit tests.

        Returns:
            None.
        '''
        self.id = None
        self.username = username
        self.database = database

    def __hash_password(self, password: str) -> str:
        '''Hashes a password using sha256 + salt.

        Args:
            password: Password to be hashed.

        Returns:
            A hashed value of password.
        '''
        salt = uuid.uuid4().hex
        return hashlib.sha256(
            salt.encode() + password.encode()
        ).hexdigest() + ':' + salt

    def __check_password(
        self, hashed_password: str, user_password: str
    ) -> bool:
        '''Checks if a password is the same as a hashed password by hashing it.

        Args:
            hashed_password: Password that has been hashed with __hash_password.
            user_password: Password that is to be checked against
                           hashed_password by being hashed itself and removing
                           the salt value.

        Returns:
            True if the passwords hash to same value, False otherwise.
        '''
        password, salt = hashed_password.split(':')
        return password == hashlib.sha256(
            salt.encode() + user_password.encode()
        ).hexdigest()

    def insert_new_user(self, password: str, email: str) -> bool:
        '''Inserts a new user into the database.

        Args:
            password: Password given by user that will be hashed prior to
                      database insertion.
            email: Email provided by user.

        Returns:
            True if self.username is new (unique), False otherwise.
        '''
        connection = sql.connect(self.database)
        cursor = connection.cursor()
        password = self.__hash_password(password)
        try:
            cursor.execute(
                'INSERT INTO Users (Username, Password, Email) VALUES (?,?,?)',
                (self.username, password, email)
            )
            connection.commit()
            connection.close()
            return True
        except sql.IntegrityError:
            connection.close()
            return False

    def login_user(self, password: str) -> bool:
        '''Checks if username/password credentials are valid.

        Args:
            password: Password provided by user attempting to login.

        Returns:
            True if username and passwords match what's stored in the database,
            False otherwise.
        '''
        connection = sql.connect(self.database)
        cursor = connection.cursor()
        cursor.execute(
            'SELECT Username, Password FROM Users WHERE Username=?',
            (self.username,)
        )
        credentials = cursor.fetchone()
        connection.close()
        if self.username == credentials[0] and self.__check_password(
            credentials[1], password
        ):
            return True
        return False

    def find_id(self) -> None:
        '''Finds the UserID of User in database using self.username.

        Args:
            None.

        Returns:
            None.
        '''
        connection = sql.connect(self.database)
        cursor = connection.cursor()
        cursor.execute(
            'SELECT UserID FROM Users WHERE Username=?', (self.username,)
        )
        row = cursor.fetchone()
        connection.close()
        self.id = row[0]

    def reset_password(self, new_password: str) -> bool:
        '''Changes user's password to a new password.

        Args:
            new_password: New password provided by user.

        Returns:
            True if new_password is not the same as previous password, False
            otherwise.
        '''
        connection = sql.connect(self.database)
        cursor = connection.cursor()
        cursor.execute(
            'SELECT Password FROM Users WHERE Username=?',
            (self.username,)
        )
        row = cursor.fetchone()
        old_password = row[0]
        if self.__check_password(old_password, new_password):
            return False
        new_password = self.__hash_password(new_password)
        cursor.execute(
            'UPDATE Users SET Password=? WHERE Username=?',
            (new_password, self.username)
        )
        connection.commit()
        connection.close()
        return True

    def get_reset_password_token(
        self, secret_key: str, id: int, expires_in=600
    ) -> None:
        '''Generates a token to be used for a secure password reset link.

        Args:
            secret_key: Application's randomly generated string used for
                        securing tokens/certificates.
            id: ID of user (corresponds to UserID in the database).
            expires_in: Integer representing the time in seconds (
                        input/60 = seconds) that the generated token remains
                        'fresh', afterwards token will become 'stale' causing
                        any url using token to return a 404 response.
                        Default is 10 minutes, this is generally a good range
                        of time, but may be changed if needed.

        Returns:
            None.
        '''
        self.id = id
        return jwt.encode(
            {'reset_password': self.id, 'exp': time.time() + expires_in},
            secret_key, algorithm='HS256'
        ).decode('utf-8')

    @staticmethod
    def find_username_with_email(database: str, email: str) -> str:
        '''Retrieves username from database with user's email.

        Args:
            database: Database to retrieve username.
            email: Email that should correspond to a username.

        Returns:
            Username if email is valid, else None.

        '''
        connection = sql.connect(database)
        cursor = connection.cursor()
        cursor.execute('SELECT Username FROM Users WHERE Email=?', (email,))
        row = cursor.fetchone()
        connection.close()
        if row:
            username = row[0]
            return username
        return None

    @staticmethod
    def find_username_with_id(database: str, id: int) -> str:
        '''Retrieves username from database with user's UserID id.

        Args:
            database: Database to retrieve username.
            id: ID that should correspond to a username.

        Returns:
            Username if id is valid, else None.

        '''
        connection = sql.connect(database)
        cursor = connection.cursor()
        cursor.execute('SELECT Username FROM Users WHERE UserID=?', (id,))
        row = cursor.fetchone()
        connection.close()
        if row:
            username = row[0]
            return username
        return None

    @staticmethod
    def find_id_with_username(database: str, username: str) -> int:
        '''Retrieves UserID from database with user's username.

        Args:
            database: Database to retrieve UserID.
            username: Username that should correspond to a UserID.

        Returns:
            UserID of user.
        '''
        connection = sql.connect(database)
        cursor = connection.cursor()
        cursor.execute('SELECT UserID FROM Users WHERE Username=?', (username,))
        row = cursor.fetchone()
        connection.close()
        if row:
            id = row[0]
            return id
        return None

    @staticmethod
    def verify_reset_password_token(token: str, secret_key: str) -> int:
        '''Verifies that a token is valid and has not yet expired.

        Args:
            token: Token generated with get_reset_password_token().
            secret_key: Application's randomly generated string used for
                        securing tokens/certificates.

        Returns:
            UserID of user trying to reset their password if the token is
            decoded successfully (i.e. is valid and not yet expired) else None.
        '''
        try:
            id = jwt.decode(token, secret_key,
                            algorithms=['HS256'])['reset_password']
        except:
            return None
        return id
