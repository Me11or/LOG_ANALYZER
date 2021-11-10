import json
import log_analyzer
import os
from pathlib import Path
import shutil
import unittest


class Test_log_analyzer(unittest.TestCase):
    def setUp(self):
        if not os.path.exists('./unittest'):
            os.mkdir('unittest')
        # Подготовка данных для config_reader
        conf_file = open('./unittest/config.ini', 'w')
        conf_file.write('[Options]\nREPORT_SIZE=100')
        conf_file.close()

        # Подготовка данных для test_serch_last_file
        open('./unittest/nginx-access-ui.log-20170628.gz', 'w').close()
        open('./unittest/nginx-access-ui.log-20170629.gz', 'w').close()
        open('./unittest/nginx-access-ui.log-20170630', 'w').close()
        open('./unittest/nginx-access-ui.log-20170701.gz', 'w').close()
        open('./unittest/nginx-access-ui.log-20170701.zip', 'w').close()

        # Подготовка данных для test_parce_file
        test_file = open('./unittest/nginx-access-ui.log-20170630', 'w')
        test_file.write(
            '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2'
            + '.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be'
            + '3" 0.390\n'
            + '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_'
            + 'name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133'
            + '\n'
            + '1.169.137.128 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 19415 "-" "S'
            + 'lotovod" "-" "1498697422-2118016444-4708-9752769" "712e90144abee9" 0.199\n'
            + '1.199.4.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/slot/4705/groups HTTP/1.1" 200 2613 "-" "Lynx'
            + '/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-3800516057-4708-9752745" "2a8281'
            + '97ae235b0b3cb" 0.704\n'
            + '1.168.65.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/internal/banner/24294027/info HTTP/1.1" 200 '
            + '407 "-" "-" "-" "1498697422-2539198130-4709-9928846" "89f7f1be37d" 0.146\n'
            + '1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx'
            + '/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161'
            + 'be3" 0.390\n'
            + '1.99.174.176 3b81f63526fa8  - [29/Jun/2017:03:50:22 +0300] "GET /api/1/photogenic_banners/list/?server_'
            + 'name=WIN7RB4 HTTP/1.1" 200 12 "-" "Python-urllib/2.7" "-" "1498697422-32900793-4708-9752770" "-" 0.133'
            + '\n'
            + '1.169.137.128 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 19415 "-" "S'
            + 'lotovod" "-" "1498697422-2118016444-4708-9752769" "712e90144abee9" 0.199\n'
            + '1.168.65.96 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/internal/banner/24294027/info HTTP/1.1" 200 '
            + '407 "-" "-" "-" "1498697422-2539198130-4709-9928846" "89f7f1be37d" 0.146\n'
        )
        test_file.close()

    def test_config_reader(self):
        config = {'REPORT_SIZE': 1000}
        config_dict = log_analyzer.read_config('./unittest/config.ini', config)
        self.assertEqual(config_dict['rep_size'], 100)

    def test_search_last_file(self):
        targetfile = log_analyzer.search_last_file('./unittest/')
        test_dir = Path('./unittest/')
        self.assertEqual(test_dir / targetfile.file_name, test_dir / 'nginx-access-ui.log-20170701.gz')

    def test_parse_file(self):
        parsed_data = log_analyzer.parse_file(Path('./unittest/nginx-access-ui.log-20170630'))
        self.assertEqual(parsed_data['all_count'], 9)
        self.assertEqual(parsed_data['err_count'], 0)

    def test_enrich_log_data(self):
        parsed_dict = dict()
        parsed_dict['/api/v2/internal/banner/24294027/info'] = dict(time_list=[])
        parsed_dict['/api/v2/internal/banner/24294027/info']['time_list'].append(0.147)
        parsed_dict['/api/v2/internal/banner/24294027/info']['time_list'].append(0.241)
        parsed_dict['/api/v2/internal/banner/24294027/info']['time_list'].append(0.167)
        parsed_dict['/api/v2/internal/banner/24294027/info']['time_list'].append(0.149)
        parsed_dict['/api/v2/banner/25019354'] = dict(time_list=[])
        parsed_dict['/api/v2/banner/25019354']['time_list'].append(0.549)
        parsed_dict['/api/v2/banner/25019354']['time_list'].append(0.949)
        parsed_data = {'parsed_dict': parsed_dict, 'all_count': 6, 'all_sum': 2.202, 'err_count': 0}
        calc_data = log_analyzer.enrich_log_data(parsed_data)
        self.assertEqual(calc_data[0]['url'], '/api/v2/banner/25019354')
        self.assertTrue((calc_data[1]['time_sum'] - 0.704) < 0.0001)

    def test_generate_json(self):
        calc_data = [
            {
                'count': 3,
                'time_avg': 0.704,
                'time_max': 0.704,
                'time_sum': 2.112,
                'url': '/api/v2/slot/4705/groups',
                'time_med': 0.704,
                'time_perc': 24.784,
                'count_perc': 20.0,
            },
            {
                'count': 6,
                'time_avg': 0.231,
                'time_max': 0.402,
                'time_sum': 1.767,
                'url': '/api/v2/banner/25019354',
                'time_med': 0.294,
                'time_perc': 37.468,
                'count_perc': 40.0,
            },
            {
                'count': 6,
                'time_avg': 0.821,
                'time_max': 0.064,
                'time_sum': 0.438,
                'url': '/api/v2/internal/banner/24294027/info',
                'time_med': 0.146,
                'time_perc': 9.288,
                'count_perc': 20.0,
            },
            {
                'count': 6,
                'time_avg': 0.233,
                'time_max': 0.454,
                'time_sum': 0.438,
                'url': '/api/v2/internal/banner/24294027/info',
                'time_med': 0.146,
                'time_perc': 9.288,
                'count_perc': 20.0,
            },
            {
                'count': 6,
                'time_avg': 0.531,
                'time_max': 0.704,
                'time_sum': 0.399,
                'url': '/api/1/photogenic_banners/list/?server_name=WIN7RB4',
                'time_med': 0.133,
                'time_perc': 8.461,
                'count_perc': 20.0,
            },
        ]

        dump_json_data = log_analyzer.generate_json(calc_data, 10)
        self.assertIsNotNone(dump_json_data)

    def test_create_report(self):
        json_data = []
        json_data.append(
            {
                'count': 3,
                'time_avg': 0.704,
                'time_max': 0.402,
                'time_sum': 2.112,
                'url': '/api/v2/slot/4705/groups',
                'time_med': 0.404,
                'time_perc': 24.784,
                'count_perc': 20,
            }
        )
        dump_json_data = json.dumps(json_data)
        log_analyzer.create_report(dump_json_data, './report_templ.html', './unittest/report-2017.06.30.html')
        self.assertTrue(os.path.exists('./unittest/report-2017.06.30.html'))

    def tearDown(self):
        shutil.rmtree('./unittest')


if __name__ == '__main__':
    unittest.main()
