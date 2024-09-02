import os
import sqlite3
from sqlite3 import Error

# Paths
current_dir = os.path.dirname(os.path.realpath(__file__))
db_path = os.path.join(current_dir, "database.db")
graded_path = os.path.join(current_dir, "..", "public", "img", "graded")

# Define rate mapping based on directory name
rate_mapping = {
    'LOW RISK': 1,
    'STEMI': 2,
    'HIGH RISK': 3
}

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

def image_exists(conn, image_name):
    """
    Check if an image already exists in the database
    :param conn: the Connection object
    :param image_name: the name of the image to check
    :return: True if the image exists, False otherwise
    """
    sql = ''' SELECT 1 FROM imageClassification WHERE photoName = ? '''
    cur = conn.cursor()
    cur.execute(sql, (image_name,))
    return cur.fetchone() is not None

def insert_image(conn, image):
    """
    Create a new image into the imageClassification table
    :param conn:
    :param image:
    :return: image id
    """
    sql = ''' INSERT INTO imageClassification(photoName, classificationSet, classificationSubSet, rate)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, image)
    return cur.lastrowid

def update_missing_rates(conn):
    """
    Update the rate for each image in the imageClassification table to 1 if it's null or empty
    :param conn:
    :return:
    """
    sql_select = ''' SELECT imageId, rate FROM imageClassification WHERE rate IS NULL OR rate = '' OR rate = 0 '''

    sql_update = ''' UPDATE imageClassification SET rate = 1 WHERE imageId = ? '''
    cur = conn.cursor()
    cur.execute(sql_select)
    rows = cur.fetchall()

    for row in rows:
        imageId = row[0]
        cur.execute(sql_update, (imageId,))
        conn.commit()
    print(f"Updated {len(rows)} images with default rate of 1.")

def main():
    conn = create_connection(db_path)
    with conn:
        for set_dir in os.listdir(graded_path):
            set_path = os.path.join(graded_path, set_dir)
            if os.path.isdir(set_path):
                for sub_dir in os.listdir(set_path):
                    sub_path = os.path.join(set_path, sub_dir)
                    rate = rate_mapping.get(set_dir, 1)  # Default rate to 1 if not in the mapping
                    print(f"Processing images from {set_dir} with rate {rate}")
                    if os.path.isdir(sub_path):
                        for image_name in os.listdir(sub_path):
                            image_path = os.path.join(sub_path, image_name)
                            if os.path.isfile(image_path) and not image_exists(conn, image_name):
                                print(f"Inserting image {image_name} with rate {rate}")
                                image = (image_name, set_dir, sub_dir, rate)
                                insert_image(conn, image)
                    else:
                        image_path = os.path.join(set_path, sub_dir)
                        if os.path.isfile(image_path) and not image_exists(conn, sub_dir):
                            print(f"Inserting image {sub_dir} with rate {rate}")
                            image = (sub_dir, set_dir, None, rate)
                            insert_image(conn, image)
        # Update missing rates after inserting images
        update_missing_rates(conn)
    conn.close()

if __name__ == '__main__':
    main()
