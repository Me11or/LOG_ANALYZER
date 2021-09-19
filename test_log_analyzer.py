import os
import re
import datetime
import collections
import gzip
import json
import string
import configparser
import logging
import argparse
import shutil
import unittest
import log_analyzer

#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';



class Test_log_analyzer(unittest.TestCase):


    def setUp(self):
        if not os.path.exists("./unittest"):
            os.mkdir("unittest")
        # Подготовка данных для config_reader
        conf_file = open("./unittest/config.ini", "w")
        conf_file.write("[Options]\nREPORT_SIZE=100")
        conf_file.close()

        # Подготовка данных для test_serch_last_file
        open("./unittest/nginx-access-ui.log-20170628.gz", "w").close()
        open("./unittest/nginx-access-ui.log-20170629.gz", "w").close()
        open("./unittest/nginx-access-ui.log-20170630", "w").close()
        open("./unittest/nginx-access-ui.log-20170701.gz", "w").close()
        open("./unittest/nginx-access-ui.log-20170701.zip", "w").close()

        
        # Подготовка данных для test_parce_file
        test_file = open("./unittest/nginx-access-ui.log-20170630", "w")
        test_file.write('1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390\n'+
                         '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133\n'+
                         '1.169.137.128 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 19415 "-" "Slotovod" "-" "1498697422-2118016444-4708-9752769" "712e90144abee9" 0.199\n'+
                         '1.199.4.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/slot/4705/groups HTTP/1.1" 200 2613 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-3800516057-4708-9752745" "2a828197ae235b0b3cb" 0.704\n'+
                         '1.168.65.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/internal/banner/24294027/info HTTP/1.1" 200 407 "-" "-" "-" "1498697422-2539198130-4709-9928846" "89f7f1be37d" 0.146\n'+
                         '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390\n'+
                         '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133\n'+
                         '1.169.137.128 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 19415 "-" "Slotovod" "-" "1498697422-2118016444-4708-9752769" "712e90144abee9" 0.199\n'+
                         '1.168.65.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/internal/banner/24294027/info HTTP/1.1" 200 407 "-" "-" "-" "1498697422-2539198130-4709-9928846" "89f7f1be37d" 0.146\n')
        test_file.close()


    def test_config_reader(self):
        config = {"REPORT_SIZE": 1000}        
        self_log_file, log_dir, rep_dir, rep_size, report_templ_path, crit_err_percent = log_analyzer.config_reader("./unittest/config.ini", config)
        self.assertEqual(rep_size,100)


    def test_serch_last_file(self):
        targetfile = log_analyzer.serch_last_file("./unittest/")
        self.assertEqual("./unittest/"+targetfile.filename,"./unittest/nginx-access-ui.log-20170701.gz")


    def test_parce_file(self):
        parced_date, all_count, all_sum, errcount = log_analyzer.parce_file("./unittest/nginx-access-ui.log-20170630")
        self.assertEqual(all_count,9)
        self.assertEqual(errcount,0)


    def test_calc_and_sort(self):
        parced_date = collections.defaultdict(list)
        parced_date["/api/v2/internal/banner/24294027/info"].append(0.147)
        parced_date["/api/v2/internal/banner/24294027/info"].append(0.241)
        parced_date["/api/v2/internal/banner/24294027/info"].append(0.167)
        parced_date["/api/v2/internal/banner/24294027/info"].append(0.149)
        parced_date["/api/v2/banner/25019354"].append(0.549)
        parced_date["/api/v2/banner/25019354"].append(0.949)
        calc_data = log_analyzer.calc_and_sort(parced_date, 6, 2.202)
        self.assertEqual(calc_data[0][4],"/api/v2/banner/25019354")
        self.assertTrue((calc_data[1][3] - 0.704) < 0.0001)


    def test_gen_json(self):
        calc_data = [[3, 0.704, 0.704, 2.112, "/api/v2/slot/4705/groups", 0.704, 24.784, 20],
                     [6, 0.231, 0.402, 1.172, "/api/v2/banner/25019354", 0.404, 25.216, 20],
                     [6, 0.821, 0.064, 1.122, "/api/v2/banner/25019355", 0.404, 10.216, 20],
                     [6, 0.233, 0.454, 1.175, "/api/v2/banner/25019356", 0.404, 20.782, 20],
                     [6, 0.531, 0.704, 1.192, "/api/v2/banner/25019357", 0.404, 20.002, 20]]
        dump_json_data = log_analyzer.gen_json(calc_data, 10)
        self.assertIsNotNone(dump_json_data) 


    def test_report_render(self):
        json_data = []
        json_data.append({"count": 3,
                          "time_avg": 0.704,
                          "time_max": 0.402,
                          "time_sum": 2.112,
                          "url": "/api/v2/slot/4705/groups",
                          "time_med": 0.404,
                          "time_perc": 24.784,
                          "count_perc": 20})        
        dump_json_data = json.dumps(json_data)
        log_analyzer.report_render(dump_json_data, "./report.html", "./unittest/report-2017.06.30.html")
        self.assertTrue(os.path.exists("./unittest/report-2017.06.30.html"))


    def tearDown(self):
        shutil.rmtree("./unittest")
        
if __name__ == "__main__":
 unittest.main()