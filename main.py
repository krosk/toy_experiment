import os
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np
import sqlite3
conn = sqlite3.connect('challenge.db')

from matplotlib import cm
import matplotlib.pyplot as plt
import matplotlib.colors as colors

import tempfile
tempFolder = tempfile.gettempdir()

# -------------------------------------------- #
#   Database
# -------------------------------------------- #
# source: https://docs.python.org/2/library/sqlite3.html

def initialize_database(database_filename, table_name):
    full_array_rmo_npy = convert_csv_to_data_npy(database_filename)
    initialize_table_for_img(table_name, full_array_rmo_npy)

def drop_table_for_img(table_name):
    c = conn.cursor()
    drop_query = f'DROP TABLE IF EXISTS {table_name}'
    c.execute(drop_query)

def create_table_for_img(table_name, column_count):
    c = conn.cursor()
    query_col = ''
    for i in range(0, column_count):
        query_col += f', col{i} real'
    create_query = f'CREATE TABLE {table_name} (depth real{query_col})'
    c.execute(create_query)

def insert_img_into_table(table_name, column_count, img_rmo_npy):
    c = conn.cursor()
    img_rmo_tuple_list = [tuple(row) for row in img_rmo_npy]
    placeholder = '?' + ',?' * column_count
    c.executemany(f'INSERT INTO {table_name} VALUES ({placeholder})', img_rmo_tuple_list)
    conn.commit()
    

def initialize_table_for_img(table_name, img_rmo_npy):
    column_count = img_rmo_npy.shape[1] - 1
    drop_table_for_img(table_name)
    create_table_for_img(table_name, column_count)
    insert_img_into_table(table_name, column_count, img_rmo_npy)

def query_img_and_depth_in_depth_range(table_name, depth_min, depth_max):
    result_depth_list = []
    result_array_rmo_list = []
    c = conn.cursor()
    range_tuple = (depth_min, depth_max)
    select_query = f'SELECT * from {table_name} WHERE depth BETWEEN ? AND ?';
    for value_tuple in c.execute(select_query, range_tuple):
        if (value_tuple != None):
            value_list = list(value_tuple)
            result_depth_list.append(value_list[0])
            result_array_rmo_list.append(value_list[1:])
    return result_depth_list, result_array_rmo_list

# -------------------------------------------- #
#   Application
# -------------------------------------------- #

def convert_csv_to_data_npy(csv_file):
    # source: https://numpy.org/doc/stable/reference/generated/numpy.genfromtxt.html
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
#   Display
# -------------------------------------------- #

def generate_plot_for_img(depth_list, img_rmo_list):
    row_count = len(depth_list)
    image_npy = np.transpose(np.reshape(img_rmo_list, (row_count, -1)))
    column_count = image_npy.shape[0]
    fig = plt.figure(figsize=(18, 8))
    colormap = cm.get_cmap('YlOrBr')
    ref_vmin = np.nanmin(image_npy)
    ref_vmax = np.nanmax(image_npy)
    x_min = depth_list[0]
    x_max = depth_list[-1]
    plt.imshow(image_npy, cmap=colormap,  aspect='auto', vmin=ref_vmin, vmax=ref_vmax, extent=[x_min, x_max, 0, column_count])
    plt.tight_layout()
    fn = os.path.join(tempFolder,'plot_' + str(np.random.randint(10000)) + '.png')
    plt.savefig(fn)
    #plt.show()
    #plt.close()
    return fn


# -------------------------------------------- #
#   Server code & API entry point
# -------------------------------------------- #
# source: https://gist.github.com/bradmontgomery/2219997

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

DATABASE_FILE = 'img.csv'
TABLE_NAME = 'img'

def run(addr, port, server_class=HTTPServer, handler_class=HandlerChallenge):
    initialize_database(DATABASE_FILE, TABLE_NAME)

    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    
    depth_list, img_rmo_list = query_img_and_depth_in_depth_range('img', 9100, 9200)
    generate_plot_for_img(depth_list, img_rmo_list)

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