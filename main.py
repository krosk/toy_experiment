import os
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np
import sqlite3
conn = sqlite3.connect('challenge.db')

# -------------------------------------------- #
#   Database
#   https://docs.python.org/2/library/sqlite3.html
# -------------------------------------------- #

def drop_table_for_img(name):
    c = conn.cursor()
    drop_query = f'DROP TABLE IF EXISTS {name}'
    c.execute(drop_query)

def create_table_for_img(name, column_count):
    c = conn.cursor()
    query_col = ''
    for i in range(0, column_count):
        query_col += f', col{i} real'
    create_query = f'CREATE TABLE {name} (depth real{query_col})'
    c.execute(create_query)

def insert_img_into_table(name, column_count, img_rmo_npy):
    c = conn.cursor()
    img_rmo_tuple_list = [tuple(row) for row in img_rmo_npy]
    placeholder = '?' + ',?' * column_count
    c.executemany(f'INSERT INTO {name} VALUES ({placeholder})', img_rmo_tuple_list)
    conn.commit()
    

def initialize_table_for_img(name, img_rmo_npy):
    column_count = img_rmo_npy.shape[1] - 1
    drop_table_for_img(name)
    create_table_for_img(name, column_count)
    insert_img_into_table(name, column_count, img_rmo_npy)

def query_img_in_range(name, depth_min, depth_max):
    c = conn.cursor()
    range_tuple = (depth_min, depth_max)
    select_query = f'SELECT * from {name} WHERE depth BETWEEN ? AND ?';
    for row in c.execute(select_query, range_tuple):
        print(c.fetchone())

# -------------------------------------------- #
#   Application
# -------------------------------------------- #

def convert_csv_to_data_npy(csv_file):
    # https://numpy.org/doc/stable/reference/generated/numpy.genfromtxt.html
    full_array_rmo_npy = np.genfromtxt(csv_file, delimiter=',', skip_header=1, skip_footer=1) 
    # INCOMPLETE: cheating because last line data is known beforehand to be invalid, one should do proper data validation by cleaning it
    return full_array_rmo_npy

def separate_data_npy_to_depth_npy_and_img_npy(full_array_rmo_npy):
    depth_index_npy = full_array_rmo_npy[:,0]
    img_rmo_npy = full_array_rmo_npy[:,1:]
    return depth_index_npy, img_rmo_npy

def downsample_img_npy(img_rmo_npy):
    # TODO
    return img_rmo_npy

# -------------------------------------------- #
#   Server code
# -------------------------------------------- #

class HandlerChallenge(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")

    def do_GET(self):
        self._set_headers()
        self.wfile.write(self._html("get"))

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        self.wfile.write(self._html("post"))

def run(addr, port, server_class=HTTPServer, handler_class=HandlerChallenge):
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)

    full_array_rmo_npy = convert_csv_to_data_npy('img.csv')
    initialize_table_for_img('img', full_array_rmo_npy)
    
    query_img_in_range('img', 9100, 9200)

    print(f"Starting httpd server on {addr}:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a simple HTTP server")
    parser.add_argument(
        "-l",
        "--listen",
        default="localhost",
        help="Specify the IP address on which the server listens",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Specify the port on which the server listens",
    )
    args = parser.parse_args()
    run(addr=args.listen, port=args.port)