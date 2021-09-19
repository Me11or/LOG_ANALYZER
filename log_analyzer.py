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

#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "REPORT_TEMPL_PATH": "./report.html",
    "CRIT_ERR_PERCENT": 30
}


def main(config_file_path):

    # Получим настройки из файла и смержим с настройками по умолчанию
    self_log_file, log_dir, rep_dir, rep_size, report_templ_path, crit_err_percent = config_reader(config_file_path, config)

    # Настроим логирование
    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S',
                        filename=self_log_file,
                        filemode='a',
                        level=logging.INFO)

    logging.info("Начинаем обработку")

    # Отловим "неожиданные ошибки", чтобы записать их в лог
    try:
        # Проверим, есть ли где искать
        if os.path.exists(log_dir):

            # Ищем самый "свежий" лог
            targetfile = serch_last_file(log_dir)

            # Если ничего не нашли, то и делать дальше нечего
            if targetfile.filename:

                log_path = log_dir+"/"+targetfile.filename
                target_report_path = rep_dir+"/report-"+targetfile.filedate.strftime('%Y.%m.%d')+".html"

                # Проверим, нет ли уже сформированного отчета по этому файлу и если есть выходим
                if not os.path.exists(target_report_path):

                    # Парсим файл лога, за одно считаем общее количество записей и общую сумму времени
                    parced_date, all_count, all_sum, errcount = parce_file(log_path)
                    if all_count == 0:
                        err_percent = 100
                    else:
                        if errcount > 0:
                            err_percent = ((errcount/all_count)*100)
                        else:
                            err_percent = 0

                    # Если превышено относительно количество обработанных с ошибкой записей, пишем в лог и выходим
                    if err_percent <= crit_err_percent:

                        # Посчитаем все необходимые значения и отсортируем по time_sum
                        calc_data = calc_and_sort(parced_date, all_count, all_sum)

                        # Берём первые rep_size записи, формируем в json формат и дампим
                        dump_json_data = gen_json(calc_data, rep_size)

                        # Рендерим отчет
                        report_render(dump_json_data, report_templ_path, target_report_path)
                        logging.info("Обработка завершена. Результат находится в {}".format(target_report_path))

                    else:
                        logging.info("Процент ошибок {}, что превышает максимальный порог {}. Прерываем выполнение.".format(err_percent, crit_err_percent))
                else:
                    logging.info("Файл {} уже был обработан ранее, результат в {}".format(targetfile.filename, target_report_path))
            else:
                logging.info("Ни один подходящий файл в директории {} не найден".format(log_dir))
        else:
            logging.info("Директория логов {} не найдена".format(log_dir))

    except Exception:
        logging.exception("Непредвиденная ошибка, запишем в лог")
        raise


def config_reader(config_file_path, def_config):

    config_file = configparser.ConfigParser()
    config_file.read(config_file_path)

    if config_file.has_option("Options", "SELF_LOG_FILE"):
        self_log_file = config_file["Options"]["SELF_LOG_FILE"]
    else:
        self_log_file = None

    if config_file.has_option("Options", "LOG_DIR"):
        log_dir = config_file["Options"]["LOG_DIR"]
    else:
        log_dir = def_config.get("LOG_DIR")

    if config_file.has_option("Options", "REPORT_DIR"):
        rep_dir = config_file["Options"]["REPORT_DIR"]
    else:
        rep_dir = def_config.get("REPORT_DIR")

    if config_file.has_option("Options", "REPORT_SIZE"):
        rep_size = int(config_file["Options"]["REPORT_SIZE"])
    else:
        rep_size = def_config.get("REPORT_SIZE")

    if config_file.has_option("Options", "REPORT_TEMPL_PATH"):
        report_templ_path = config_file["Options"]["REPORT_TEMPL_PATH"]
    else:
        report_templ_path = def_config.get("REPORT_TEMPL_PATH")

    if config_file.has_option("Options", "CRIT_ERR_PERCENT"):
        crit_err_percent = int(config_file["Options"]["CRIT_ERR_PERCENT"])
    else:
        crit_err_percent = def_config.get("CRIT_ERR_PERCENT")

    return self_log_file, log_dir, rep_dir, rep_size, report_templ_path, crit_err_percent


def serch_last_file(log_dir):
    lastdate = None
    lastfilename = None
    lastfiledata = collections.namedtuple('lastfiledata', ['filename', 'filedate'])
    re_serch_file = re.compile(r"^nginx-access-ui.log-\d{8}.gz$|^nginx-access-ui.log-\d{8}$")
    re_get_date = re.compile(r'\d{4}\d{2}\d{2}')
    try:
        for file in os.listdir(log_dir):
            match_file = re.search(re_serch_file, file)
            if match_file:
                match_date = re.search(re_get_date, file)
                date = datetime.datetime.strptime(match_date.group(), '%Y%m%d').date()
                if lastdate is None:
                    lastdate = date
                    lastfilename = file
                if lastdate < date:
                    lastdate = date
                    lastfilename = file
        return lastfiledata(lastfilename, lastdate)
    except Exception as error:
        logging.info("Ошибка поиска файла: {}".format(error))
        return None


def parce_file(file_path):
    count = 0
    sum = 0
    errcount = 0
    data_dict = collections.defaultdict(list)

    if file_path.endswith(".gz"):
        file = gzip.open(file_path, 'rb')
    else:
        file = open(file_path, 'rb')

    re_url = re.compile(r"GET (.+?) HTTP")
    re_timedata = re.compile(r"\d+[.]\d*$")

    open_file_gen = (st for st in file)

    for item in open_file_gen:
        count += 1
        item = item.decode("UTF-8")
        try:
            url = re.search(re_url, item).group(1)
            timedata = float(re.search(re_timedata, item).group())
            sum += timedata
            data_dict[url].append(timedata)
        except Exception:
            errcount += 1
            count -= 1
    file.close()
    return data_dict, count, sum, errcount


def calc_and_sort(parced_date, all_count, all_sum):
    calculated_data = []
    for url_str in parced_date:
        local_count = len(parced_date[url_str])
        local_sum = sum(parced_date[url_str])
        # Запишем посчитанные данные в список списков и отсортируем по сумме
        calculated_data.append([local_count,                   #count
                                local_sum/local_count,         #time_avg
                                max(parced_date[url_str]),     #time_max
                                local_sum,                     #time_sum
                                url_str,                       #url
                                median(parced_date[url_str]),  #time_med
                                local_sum*100/all_sum,         #time_perc
                                local_count*100/all_count])    #count_perc
    calculated_data.sort(key=lambda x: x[3], reverse=True)
    return calculated_data


def gen_json(data, max_size):
    json_data = []
    for rec in data:
        json_data.append({"count": rec[0],
                          "time_avg": round(rec[1], 3),
                          "time_max": round(rec[2], 3),
                          "time_sum": round(rec[3], 3),
                          "url": rec[4],
                          "time_med": round(rec[5], 3),
                          "time_perc": round(rec[6], 3),
                          "count_perc": round(rec[7], 3)})
        if len(json_data) >= max_size:
            break
    return json.dumps(json_data)


def report_render(json_data, report_templ_path, target_report_path):
    report_template = open(report_templ_path, 'r')
    readed_templ = string.Template(report_template.read())
    report_template.close()
    rendered_report = readed_templ.safe_substitute(table_json=json_data)
    result_report = open(target_report_path, 'w')
    result_report.write(rendered_report)
    result_report.close()


def median(list):
    n = len(list)
    index = n // 2
    if n % 2:
        return sorted(list)[index]
    return sum(sorted(list)[index - 1:index + 1]) / 2


if __name__ == "__main__":
    #Обработаем полученные параметры(в частности путь до файла настрокйи)
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--config', type=str, dest='conf_path', default='./config.ini')
    args = arg_parser.parse_args()

    #Если не нашли файл настройки, то как по требованиям взрываемся ошибкой
    if os.path.exists(args.conf_path):
        main(args.conf_path)
    else:
        raise ValueError("Файл настройки {} не найден".format(args.conf_path))
