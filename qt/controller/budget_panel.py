# Copyright 2019 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QVBoxLayout, QFormLayout, QLabel,
    QDialogButtonBox)

from core.trans import trget
from ..support.date_edit import DateEdit
from .panel import Panel

tr = trget('ui')

class BudgetPanel(Panel):
    FIELDS = [
        ('startDateEdit', 'start_date'),
    ]
    PERSISTENT_NAME = 'budgetPanel'

    def __init__(self, model, mainwindow):
        Panel.__init__(self, mainwindow)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self._setupUi()
        self.model = model

        # TODO: Solve dual recurrence problem
        """
        self.repeatTypeComboBox = ComboboxModel(
            model=self.model.repeat_type_list, view=self.repeatTypeComboBoxView)
        """

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def _setupUi(self):
        self.setWindowTitle(tr("Budget Info"))
        self.resize(230, 230)
        self.setModal(True)
        self.verticalLayout = QVBoxLayout(self)
        self.formLayout = QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.label_1 = QLabel(tr("Start Date:"))
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_1)
        self.startDateEdit = DateEdit(self)
        self.startDateEdit.setMaximumWidth(120)
        self.label_1.setBuddy(self.startDateEdit)
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.startDateEdit)
        """
        self.label_2 = QLabel(tr("Budget Cycle:"))
        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)
        self.repeatTypeComboBoxView = QComboBox(self)
        self.label_2.setBuddy(self.repeatTypeComboBoxView)
        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.repeatTypeComboBoxView)
        self.label_3 = QLabel(tr("Budget Periods:"))
        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_3)
        self.repeatEverySpinBox = QSpinBox(self)
        self.repeatEverySpinBox.setMinimum(1)
        self.label_3.setBuddy(self.repeatEverySpinBox)
        self.formLayout.addWidget(self.repeatEverySpinBox)
        self.repeatEveryDescLabel = QLabel(self)
        # TODO: figure how to add this to formlayout, maybe hbox the spinbox + label?
        self.verticalLayout.addWidget(self.repeatEveryDescLabel)
        """
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Save)
        self.verticalLayout.addWidget(self.buttonBox)

