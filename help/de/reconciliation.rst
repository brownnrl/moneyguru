Wertstellung
============

Die Wertstellung von Transaktionen (Valuta) erleichtert den Abgleich zwischen Bankauszügen und den Transaktionen in moneyGuru. Nach dem Import von Kontodaten beziehungsweise dem Erfassen von Kontotransaktionen können so noch einmal alle Transaktionen kontrolliert werden. Sind alle Daten korrekt, so können die neu erfassten Transaktionen wertgestellt werden.

Um das zu erreichen, öffnen Sie das entsprechende Konto, wählen Sie die Schaltfläche "Wertstellung" oder drücken |cmd_shift|\ R um in den Wertstellungsmodus zu wechseln. Damit bekommen Sie ein Kontrollkästchen vor jede Transaktion. Um eine Transaktion wertzustellen, aktivieren Sie einfach das entsprechende Kontrollkästchen. Sie erreichen das auch durch Auswahl der Transaktion und Drücken der Leertaste. Nachdem Sie alle Transaktionen kontrolliert und aktiviert haben, schließen Sie den Wertstellungsmodus wieder, damit werden alle "aktivierten" Transaktionen mit einem grünen Häkchen versehen: |reconciliation_checkmark|.

Sollte das Datum der Transaktion vom Wertstellungsdatum abweichen, so können Sie mit Hilfe von |cmd|\ J die Spalte "Wertstellungsdatum" einblenden. Sobald eine Transaktion wertgestellt ist, so wird hier automatisch das Transaktionsdatum übernommen, Sie können es aber entsprechend ändern, um es an das korrekte Valutadatum anzupassen. Ändern Sie das Wertstellungsdatum einer Transaktion, die noch nicht wertgestellt wurde, so wird sie nach Abschluss der Änderungen entsprechend wertgestellt.

Im Wertstellungsmodus wird in der Spalte "Saldo" nur der Saldo über alle *wertgestellten* Transaktionen (Häkchen aktiviert) berechnet. Dadurch sollte es noch einfacher sein, einen Abgleich den Bankauszügen vornehmen zu können. It's important to note that the balance, when in reconciliation mode, is calculated by following the **Reconciliation Date** entry order. Therefore, if your reconciliation dates differ from your entry dates, you should sort your table by Reconciliation date if you want your balances to make any sense in reconciliation mode.

.. |reconciliation_checkmark| image:: image/reconciliation_checkmark.png
