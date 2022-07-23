import os
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QFileDialog
import PyQt6.QtGui as QtGui
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PIL import Image
from PIL.ImageQt import ImageQt
import pytesseract
from pdf2image import convert_from_path

app = QApplication([])

class Box:
    def __init__(self, x0, y0, x1, y1):
        if x0 < x1:
            self.left = x0
            self.right = x1
        else:
            self.left = x1
            self.right = x0
        if y0 < y1:
            self.upper = y0
            self.lower = y1
        else:
            self.upper = y1
            self.lower = y0

        self.ocr_str = ''
        self.drawn = False

    def scale(self, scale_x, scale_y):
        return Box(self.left*scale_x, self.upper*scale_y, self.right*scale_x, self.lower*scale_y)

    def tup(self):
        return (self.left, self.upper, self.right, self.lower)

    def inside(self, x, y):
        return x >= self.left and x <= self.right and y >= self.upper and y <= self.lower

class FormWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.mouse_press_pos = None
        self.mouse_current_pos = None
        self.drawing_box = False
        self.boxes = []
        self.show_ocr = False
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.FileMode.AnyFile)
        filenames = []
        if dlg.exec():
            filenames = dlg.selectedFiles()
        
        if len(filenames) == 0:
            print("No file selected")
            exit(0)

        page_imgs = convert_from_path(filenames[0], 200, poppler_path=f'{os.path.dirname(os.path.realpath(__file__))}/poppler-22.04.0/Library/bin')
        self.setWindowTitle(filenames[0])
        self.img: Image = page_imgs[0]
        self.cv_img = np.array(self.img)
        self.cv_img = self.cv_img[:, :, ::-1]
        self.img_qt = ImageQt(self.img)
        self.pixmap = QPixmap.fromImage(self.img_qt)
        self.scale = .5
        self.swidth = int(self.img.width*self.scale)
        self.sheight = int(self.img.height*self.scale)
        self.setGeometry(0, 0, self.swidth, self.sheight)
        self.pixmap = self.pixmap.scaled(self.swidth, self.sheight, aspectRatioMode=Qt.AspectRatioMode.IgnoreAspectRatio, transformMode=Qt.TransformationMode.SmoothTransformation)

        self.img_label = QLabel(self)
        self.img_label.adjustSize()
        self.show()
    
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.mouse_press_pos = event.pos()
        self.mouse_current_pos = None
        if event.button() == Qt.MouseButton.RightButton:
            self.boxes = [b for b in self.boxes if not b.inside(event.pos().x(), event.pos().y())]
        elif event.button() == Qt.MouseButton.LeftButton:
            self.drawing_box = True
        self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.mouse_current_pos = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            x0 = self.mouse_press_pos.x()
            y0 = self.mouse_press_pos.y()
            x1 = self.mouse_current_pos.x()
            y1 = self.mouse_current_pos.y()
            if x0 == x1 or y0 == y1:
                self.drawing_box = False
                return

            box = Box(x0, y0, x1, y1)
            self.boxes.append(box)
            
            full_h = self.img.size[1]
            full_w = self.img.size[0]
            img_h = self.pixmap.height()
            img_w = self.pixmap.width()
            scale_h = full_h // img_h
            scale_w = full_w // img_w
            scaled = box.scale(scale_w, scale_h)
            x = scaled.left
            y = scaled.upper
            width = scaled.right - scaled.left
            height = scaled.lower - scaled.upper # lower y-coord is a higher number in the image array
            box_img = self.cv_img[y:y+height, x:x+width]
            box.ocr_str = pytesseract.image_to_string(box_img)

            self.update()
            self.drawing_box = False

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.mouse_current_pos = event.pos()
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setBrush(QtGui.QBrush(QtGui.QColor(100, 10, 10, 40)))
        self.pixmap = QPixmap.fromImage(self.img_qt).scaled(self.swidth, self.sheight, aspectRatioMode=Qt.AspectRatioMode.IgnoreAspectRatio, transformMode=Qt.TransformationMode.SmoothTransformation)
        qpimg = QtGui.QPainter(self.pixmap)
        qpimg.setFont(QtGui.QFont("Arial", 15))
        qpimg.setBrush(QtGui.QBrush(QtGui.QColor(100, 10, 10, 40)))
        for b in self.boxes:
            qpimg.drawRect(QRect(QPoint(b.left, b.upper),QPoint(b.right, b.lower)))
            qpimg.drawText(QPoint(b.left-100, b.lower), b.ocr_str)
            b.drawn = True
        
        qp.drawPixmap(self.rect(), self.pixmap)
        if self.drawing_box and self.mouse_press_pos is not None and self.mouse_current_pos is not None:
            qp.drawRect(QRect(self.mouse_press_pos , self.mouse_current_pos))

window = FormWindow()
app.exec()
