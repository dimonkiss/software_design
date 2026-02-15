import pytest
from src.gui.main_window import MainWindow
from src.gui.canvas.items import BlockItem


@pytest.fixture
def app(qtbot):
    """Створює головне вікно для тестів."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_gui_add_remove_thread(app, qtbot):
    """Додавання та видалення вкладки потоку."""
    initial_count = app.tab_widget.count()

    # 1. Додаємо
    app.add_new_thread()
    assert app.tab_widget.count() == initial_count + 1
    assert len(app.project.threads) == initial_count + 1

    # 2. Видаляємо (останній)
    last_index = app.tab_widget.count() - 1
    app.close_thread_tab(last_index)
    assert app.tab_widget.count() == initial_count
    assert len(app.project.threads) == initial_count


def test_gui_add_block_via_toolbar(app, qtbot):
    """Додавання блоку через код (імітація кнопки)."""
    # Отримуємо поточну вкладку
    tab = app.tab_widget.currentWidget()
    initial_blocks = len(tab.thread_model.blocks)

    # Додаємо блок ASSIGN
    app.add_block_to_current("ASSIGN")

    assert len(tab.thread_model.blocks) == initial_blocks + 1

    # Перевіряємо, чи з'явився графічний елемент на сцені
    scene_items = tab.view.scene.items()
    blocks = [i for i in scene_items if isinstance(i, BlockItem)]
    assert len(blocks) == initial_blocks + 1
    assert blocks[0].model.type == "ASSIGN"


def test_gui_property_editor_interaction(app, qtbot):
    """Вибір блоку і зміна властивостей."""
    app.add_block_to_current("ASSIGN")
    tab = app.tab_widget.currentWidget()

    # Знаходимо BlockItem на сцені
    block_item = [i for i in tab.view.scene.items() if isinstance(i, BlockItem)][0]

    # Імітуємо вибір (клік)
    tab.view.scene.clearSelection()
    block_item.setSelected(True)

    # Викликаємо обробник події вручну, бо qtbot не завжди тригерить сигнали сцени
    app.on_selection_changed()

    # Перевіряємо, чи редактор властивостей підхопив блок
    assert app.property_editor.current_block_item == block_item

    # Змінюємо значення у спінбоксі редактора
    # Знаходимо QSpinBox у формі (він там один для ASSIGN value)
    spinbox = app.property_editor.findChild(type(app.property_editor.val_spin))

    # Встановлюємо значення 777
    spinbox.setValue(777)

    # Перевіряємо, чи оновилась модель
    assert block_item.model.value == 777