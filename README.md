# LOG_ANALYZER
Программа анализирующая логи определенного формата(ДЗ по курсу Python Developer. Professional)

Для работы программы необходимо создать файл настроек. Для этого нужно создать файл config.ini либо в директории со скриптом, либо передать скрипту в параметре --config путь до файла настроек. Файл формата ini, все настройки находятся в секции "Options", и может содержать следующие настройки:
- SELF_LOG_FILE - путь до файла, для ведения собственного лога скрипта
- LOG_DIR - директория поиска лога для анализа
- REPORT_DIR - директория куда будет сохранятся отчет с результатом анализа
- REPORT_SIZE - количество записей с наибольшим суммарным временем выполнения которые попадут в отчет
- REPORT_TEMPL_PATH - путь до файла шаблона отчета
- CRIT_ERR_PERCENT - процент обработанных с ошибкой записей при котором отчет формироваться не будет
Все неуказанные в файле настройки будут браться из настроек по умолчанию

Для запуска можно использовать команды:
- python3 log_analyzer.py --config <путь к файлу настроек>
- python3 log_analyzer.py

Для запуска тестов можно использовать команду:
- python3 -m unittest -v test_log_analyzer.py


    booksДомашнее задание/проектная работа разработано(-на) для курса "Название курса"
<h3 dir="auto"><g-emoji class="g-emoji" alias="books" fallback-src="https://github.githubassets.com/images/icons/emoji/unicode/1f4da.png">📚</g-emoji><strong>Домашнее задание разработано для курса "<a href="https://otus.ru/lessons/python-professional/" rel="nofollow">Python Developer. Professional</a>"</strong></h3>
