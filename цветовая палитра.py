import shutil
import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QInputDialog, QListWidgetItem, QMenu, QLabel,\
    QListWidget, QPushButton, QLineEdit
from PyQt5.QtGui import QPixmap
from PyQt5 import uic
from PyQt5 import QtCore, QtGui, QtWidgets
from colorthief import ColorThief
from PIL import Image
import os
import sqlite3


def sqlite3_read_pictures_specs_from_db(data_base, table):
    """
    Функция для чтения сведений о рисунках, записаных в указанной таблице (table)
    указанной базы данных (data_base) сведения включают id, описание рисунка, путь из которого рисунок импортирован
    """
    con = sqlite3.connect(str(data_base))
    cur = con.cursor()
    try:
        query = 'SELECT id, description, path FROM ' + table
        cur.execute(query)
        data = cur.fetchall()
    except sqlite3.OperationalError:
        data = None
    cur.close()
    con.close()
    return data


def sqlite3_simple_pict_import(data_base, table, pict_path, description):
    """
    Функция для создания таблицы в базе данных с использование СУБД sqlite3
    Таблица создается для хранения рисунков в формате BLOB, после
    создания таблицы туда помещается рисунок по пути pict_path
    """
    con = sqlite3.connect(data_base)
    cur = con.cursor()
    query_creation = 'CREATE TABLE IF NOT EXISTS '+str(table) + \
                     '(id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, path TEXT,data BLOB)'
    cur.execute(query_creation)
    binary_pict = import_pict_binary(pict_path)
    data = (description, pict_path, binary_pict)
    query = 'INSERT INTO '+table+' (description, path, data)  VALUES(?, ?, ?)'
    cur.execute(query, data)
    con.commit()
    cur.close()
    con.close()


def clean_table(database, table):
    con = sqlite3.connect(database)
    cur = con.cursor()
    query = 'DELETE FROM ' + table
    cur.execute(query)
    con.commit()
    cur.close()
    con.close()


def export_pict_from_sql(data_base, table, record_id, path):
    """
    Чтение рисунка из таблицы (table) базы данных (data_base) по уникальному идентификатору (id)
    и запись его с тем же именем, что и указано в базе данных, но по новому пути (new_path)
    """
    con = sqlite3.connect(data_base)
    cur = con.cursor()
    query = 'SELECT data, path, description FROM ' + table + ' WHERE id = "' + str(record_id) + '"'
    cur.execute(query)
    record = cur.fetchone()
    pict_binary = record[0]
    write_pict_from_binary(path, pict_binary)
    return


def sqlite3_simple_delete_record(data_base, table, id_column, record_id):
    """
    Функция для удаления записи в указанной таблице, указанной базы данных
    по названию колонки (id column) и значению ячейки (record_id) в указанной колонке
    """
    con = sqlite3.connect(data_base)
    cur = con.cursor()
    query = 'DELETE FROM '+table+' WHERE '+id_column+" = '" + str(record_id) + "'"
    cur.execute(query)
    con.commit()
    cur.close()
    con.close()


def import_pict_binary(pict_path):
    f = open(pict_path, 'rb')
    pict_binary = f.read()
    return pict_binary


def write_pict_from_binary(file_path, pict_binary):
    f = open(file_path, 'wb')
    f.write(pict_binary)


def make_dir_if_it_is_not_exists():
    directory = os.getcwd() + '\\tmp'
    if not os.path.exists(directory):
        os.makedirs(directory)

    return directory


def add_element_to_list_widget(item_id, item_name, list_widget, icon):
    item = QListWidgetItem()  # Cоздаём объект QListWigetItem
    item.setIcon(QtGui.QIcon(icon))  # Добавляем объект иконки (Qicon) для объекта QListWigetItem
    item.setText(item_name)  # Добавляем название итема

    item.setData(QtCore.Qt.UserRole, item_id)

    list_widget.addItem(item)


class ColorPalette(QMainWindow):
    tmp_dir = None
    list_of_palls: QListWidget
    palette: QLabel
    choose_pic: QPushButton
    create_pal: QPushButton
    save_pal: QPushButton
    rgb_colors: QLineEdit
    clear_database: QPushButton
    database = '.\\db_data\\PictDatabase.db'
    palettes_table_name = 'palettes'

    def __init__(self):
        super().__init__()
        uic.loadUi('палитра.ui', self)
        self.setWindowTitle('Color Palette')
        self.pixmap = QPixmap('gbackground.png')
        self.palette.setPixmap(self.pixmap)
        self.im = Image.new("RGB", (300, 300), (255, 255, 255))
        self.save_pal.clicked.connect(self.save_pal_to_db)
        self.create_pal.clicked.connect(self.show_palette)
        self.choose_pic.clicked.connect(self.open_picture)
        self.clear_database.clicked.connect(self.cleanup)
        self.rgb_colors.setReadOnly(True)
        self.list_of_palls.installEventFilter(self)

        self.show()

        self.save_pal_to_db()

    # Переопределяем системный метод для отлова событий
    def eventFilter(self, source, event):
        # Отлавливаем тип события открытия контекстного меню
        if (event.type() == QtCore.QEvent.ContextMenu and
                source is self.list_of_palls):
            # Создаем блок с контекстным меню
            menu = QMenu()
            menu.addAction('Экспорт')
            menu.addAction('Удалить')

            # Помещаем контекстное меню в место клика
            action = menu.exec(event.globalPos())

            if action:
                # Получаем элемент списка по месту клика
                item = source.itemAt(event.pos())
                # Вычисляем какая из кнопок контекстного меню была нажата
                # и выполняем соответствующее действие
                if action.text() == 'Удалить':
                    self.delete_item(item)
                elif action.text() == 'Экспорт':
                    self.export_item(item)

            return True

        return super(ColorPalette, self).eventFilter(source, event)

    def delete_item(self, item: QListWidgetItem):
        # Извлекаем id элемента сохраненного в данных блока при создании
        item_id = item.data(QtCore.Qt.UserRole)
        # Удаляем строку из базы данных
        sqlite3_simple_delete_record(self.database, self.palettes_table_name, 'id', item_id)

        self.save_pal_to_db()

    def export_item(self, item: QListWidgetItem):
        item_id = item.data(QtCore.Qt.UserRole)

        path = QFileDialog.getSaveFileName(self, 'Сохранить палитру', '',
                                           'Палитра (*.jpg);;Палитра (*.png);;Палитра (*.jpeg)')[0]

        if path:
            export_pict_from_sql(self.database, self.palettes_table_name, item_id, path)

    def cleanup(self):
        clean_table(self.database, self.palettes_table_name)  # Очищаем таблицу с палитрами

    def open_picture(self):
        self.path = QFileDialog.getOpenFileName(
            self, 'Выбрать картинку', '',
            'Картинка (*.jpg);;Картинка (*.png);;Картинка (*.jpeg)')[0]
        self.palette.setPixmap(QPixmap(self.path))
        self.create_pal.setEnabled(True)

    def show_palette(self):
        colors = list()
        color_thief = ColorThief(self.path)
        palette = color_thief.get_palette(color_count=6)
        x = 0
        y = 0
        for z in palette:
            self.im.paste(Image.new('RGB', (300, 50), z), (x, y))
            y += 50
            colors.append(str(z))
        self.im.save('palette.jpg')
        self.palette.setPixmap(QPixmap('palette.jpg'))
        self.rgb_colors.setText(", ".join(colors))
        database = '.\\db_data\\PictDatabase.db'
        table = 'palettes'
        description, ok_pressed = QInputDialog.getText(self, "Название палитры", "Введите название палитры")

        while ok_pressed and not description:
            description, ok_pressed = QInputDialog.getText(self, "Название палитры", "Введите название палитры")

        if not ok_pressed or not description:
            return

        pict_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'palette.jpg')
        sqlite3_simple_pict_import(database, table, pict_path, description)
        os.remove(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'palette.jpg'))
        self.save_pal.setEnabled(True)

    def save_pal_to_db(self):
        data = sqlite3_read_pictures_specs_from_db(self.database, self.palettes_table_name)
        if data is None:
            pass
        else:
            self.tmp_dir = make_dir_if_it_is_not_exists()

            self.list_of_palls.clear()
            for pict_specs in data:
                id, description, path = pict_specs
                # Создаем временный путь к файлу
                temporary_path = self.tmp_dir + '\\' + str(id) + '.jpg'
                if not os.path.exists(temporary_path):
                    # Экспортируем рисунок по временному пути
                    export_pict_from_sql(self.database, self.palettes_table_name, id, temporary_path)

                # Создаем элемент QListWidgetItem и добавляем его в список
                add_element_to_list_widget(id, '#' + str(id) + '. ' + str(description), self.list_of_palls,
                                               temporary_path)
        self.save_pal.setEnabled(False)
        self.create_pal.setEnabled(False)
        self.palette.setPixmap(self.pixmap)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon('icon.jpg'))
    app.setStyle('Fusion')
    ex = ColorPalette()
    exit_code = app.exec_()
    shutil.rmtree(ex.tmp_dir)
    sys.exit(exit_code)
