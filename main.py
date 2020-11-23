import os
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

from urllib.parse import urlparse

import numpy as np
import sqlite3
conn = sqlite3.connect('challenge.db')

from matplotlib import cm
import matplotlib.pyplot as plt
import matplotlib.colors as colors

import tempfile
tempFolder = tempfile.gettempdir()

import traceback

# -------------------------------------------- #
#   Database
# -------------------------------------------- #
# source: https://docs.python.org/2/library/sqlite3.html

def initialize_database(database_filename, table_name, target_column_count):
    full_array_rmo_npy = convert_csv_to_data_npy(database_filename)
    full_array_rmo_npy = downsample_data_npy(full_array_rmo_npy, target_column_count)
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

def get_depth_min_max_from_query(path):
    # source: https://stackoverflow.com/questions/8928730/processing-http-get-input-parameter-on-server-side-in-python
    query = urlparse(path).query
    query_components_list = query.split("&")
    query_components = {}
    for query_component in query_components_list:
        query_key_value = query_component.split('=')
        query_components[query_key_value[0]] = query_key_value[1]
    depth_min = float(query_components['depth_min'])
    depth_max = float(query_components['depth_max'])
    return depth_min, depth_max

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

def downsample_data_npy(full_array_rmo_npy, target_column_count):
    depth_index_npy, img_rmo_npy = separate_data_npy_to_depth_npy_and_img_npy(full_array_rmo_npy)
    row_count = len(depth_index_npy)
    # resample image data only
    img_rmo_resampled_npy = [ np.interp(np.linspace(0, len(row) - 1, target_column_count), np.arange(0, len(row)), row) for row in img_rmo_npy]
    img_rmo_resampled_npy = np.array(img_rmo_resampled_npy)
    # reconstruct the data, which is row count x (depth column + target_column_count)
    reconstructed_full_array_rmo_npy = np.zeros((row_count, target_column_count + 1))
    reconstructed_full_array_rmo_npy[:,0] = depth_index_npy
    reconstructed_full_array_rmo_npy[:,1:] = img_rmo_resampled_npy
    return reconstructed_full_array_rmo_npy

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

def generate_file_stream(image_filename):
    file = open(image_filename, "rb")
    file_stream = file.read()
    file.close()
    return file_stream

# -------------------------------------------- #
#   Server code & API entry point
# -------------------------------------------- #
# source: https://gist.github.com/bradmontgomery/2219997

class HandlerChallenge(BaseHTTPRequestHandler):
    def _set_png_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "image/png")
        self.end_headers()

    def _set_text_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def _html(self, message):
        content = f"<html><body><h1>{message}</h1></body></html>"
        return content.encode("utf8")

    def do_GET(self):
        try:
            depth_min, depth_max = get_depth_min_max_from_query(self.path)
            depth_list, img_rmo_list = query_img_and_depth_in_depth_range(TABLE_NAME, depth_min, depth_max)
            image_filename = generate_plot_for_img(depth_list, img_rmo_list)
            self._set_png_headers()
            self.wfile.write(generate_file_stream(image_filename))
        except:
            traceback.print_exc()
            self._set_text_headers()
            self.wfile.write(self._html("Require query ?depth_min= &depth_max= "))

DATABASE_FILE = 'img.csv'
TABLE_NAME = 'img'
TABLE_IMAGE_COLUMN_COUNT = 150

def run(addr, port, server_class=HTTPServer, handler_class=HandlerChallenge):
    initialize_database(DATABASE_FILE, TABLE_NAME, TABLE_IMAGE_COLUMN_COUNT)
    
    server_address = (addr, port)
    httpd = server_class(server_address, handler_class)
    
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