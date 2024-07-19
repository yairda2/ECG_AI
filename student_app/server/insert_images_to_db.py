# this script need to be run only once to insert images to the database
# the structure of the database is defined in the graded dir in public/img/graded
# the Set is the base dir HIGH RISK STEMI and LOW RISK
# the sub dirs are the Subset
# for LOW RISK not subset dirs


# go on this dirs and if for each image if she not in the db by here name insert her to the db


import os
import sqlite3
from sqlite3 import Error
from PIL import Image

# Phats
current_dir = os.path.dirname(os.path.realpath(__file__))
db_path = os.path.join(current_dir, "database.db")
graded_path = os.path.join(current_dir, "..", "public", "img", "graded")


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn


def insert_image(conn, image):
    """
    Create a new image into the images table
    :param conn:
    :param image:
    :return: image id
    """
    sql = ''' INSERT INTO imageClassification(photoName,classificationSet,classificationSubSet)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, image)
    return cur.lastrowid


def main():
    conn = create_connection(db_path)
    with conn:
        for set_dir in os.listdir(graded_path):
            set_path = os.path.join(graded_path, set_dir)
            if os.path.isdir(set_path):
                for sub_dir in os.listdir(set_path):
                    sub_path = os.path.join(set_path, sub_dir)
                    if os.path.isdir(sub_path):
                        for image_name in os.listdir(sub_path):
                            image_path = os.path.join(sub_path, image_name)
                            if os.path.isfile(image_path):
                                image = (image_name, set_dir, sub_dir)
                                insert_image(conn, image)
                    else:
                        image_path = os.path.join(set_path, sub_dir)
                        if os.path.isfile(image_path):
                            image = (sub_dir, set_dir, None)
                            insert_image(conn, image)
    conn.close()


if __name__ == '__main__':
    main()
