from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLabel, QFileDialog, QProgressBar, 
                           QListWidget, QMessageBox, QHBoxLayout, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import os

class PDFListItem(QWidget):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Nome do arquivo
        self.label = QLabel(os.path.basename(self.file_path))
        self.label.setStyleSheet("""
            QLabel {
                padding: 5px;
                border: none;
            }
        """)
        layout.addWidget(self.label)
        
        # Botão de exclusão
        self.delete_button = QPushButton("X")
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
        """)
        layout.addWidget(self.delete_button)
        
        self.setLayout(layout)

class PDFMergerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        try:
            from PyPDF2 import PdfMerger
            import tempfile
            
            merger = PdfMerger()
            total_files = len(self.files)
            
            for i, file_path in enumerate(self.files):
                merger.append(file_path)
                self.progress.emit(int((i + 1) / total_files * 100))
            
            output_path = os.path.join(tempfile.gettempdir(), 'merged.pdf')
            merger.write(output_path)
            merger.close()
            
            self.finished.emit(output_path)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Compilador de PDFs")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #1E88E5;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1E88E5;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Botão para selecionar arquivos
        self.select_button = QPushButton("Selecionar PDFs")
        self.select_button.clicked.connect(self.select_files)
        layout.addWidget(self.select_button)
        
        # Lista de arquivos
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)
        
        # Botão para mesclar
        self.merge_button = QPushButton("Mesclar PDFs")
        self.merge_button.clicked.connect(self.merge_pdfs)
        self.merge_button.setEnabled(False)
        layout.addWidget(self.merge_button)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.selected_files = []
        self.merger_thread = None

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar Arquivos PDF",
            "",
            "Arquivos PDF (*.pdf)"
        )
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.add_file_to_list(file)
            
            self.merge_button.setEnabled(len(self.selected_files) > 0)
            self.status_label.setText(f"Selecionados {len(self.selected_files)} arquivos")

    def add_file_to_list(self, file_path):
        item = QListWidgetItem()
        self.file_list.addItem(item)
        
        widget = PDFListItem(file_path)
        item.setSizeHint(widget.sizeHint())
        self.file_list.setItemWidget(item, widget)
        
        # Conectar o botão de exclusão
        widget.delete_button.clicked.connect(lambda: self.remove_file(file_path, item))

    def remove_file(self, file_path, item):
        try:
            # Remover da lista de arquivos
            self.selected_files.remove(file_path)
            
            # Remover o item da lista visual
            self.file_list.takeItem(self.file_list.row(item))
            
            # Atualizar status
            self.status_label.setText(f"Selecionados {len(self.selected_files)} arquivos")
            self.merge_button.setEnabled(len(self.selected_files) > 0)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao remover arquivo: {str(e)}")

    def merge_pdfs(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo PDF selecionado!")
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Processando...")
            self.merge_button.setEnabled(False)
            self.select_button.setEnabled(False)
            
            self.merger_thread = PDFMergerThread(self.selected_files)
            self.merger_thread.progress.connect(self.update_progress)
            self.merger_thread.finished.connect(self.merge_finished)
            self.merger_thread.error.connect(self.merge_error)
            self.merger_thread.start()
        except Exception as e:
            self.merge_error(str(e))

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def merge_finished(self, output_path):
        try:
            self.progress_bar.setVisible(False)
            self.status_label.setText("PDFs mesclados com sucesso!")
            self.merge_button.setEnabled(True)
            self.select_button.setEnabled(True)
            
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar PDF Mesclado",
                "",
                "Arquivos PDF (*.pdf)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(output_path, save_path)
                QMessageBox.information(self, "Sucesso", "PDFs mesclados e salvos com sucesso!")
            else:
                QMessageBox.information(self, "Informação", "Operação cancelada pelo usuário.")
        except Exception as e:
            self.merge_error(str(e))

    def merge_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.status_label.setText("")
        self.merge_button.setEnabled(True)
        self.select_button.setEnabled(True)
        QMessageBox.critical(self, "Erro", f"Erro ao mesclar PDFs: {error_message}") 