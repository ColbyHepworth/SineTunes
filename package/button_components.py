from discord_slash import ButtonStyle
from discord_slash.utils.manage_components import create_actionrow


class Button:

    def __init__(self, data):
        self._data = data
        if "label" in data:
            self._label = data["label"]
        else:
            self._label = None
        self._custom_id = data["custom_id"]
        self._style = data["style"]
        self._emoji = data["emoji"]
        self._index = None

    @property
    def data(self):
        return self._data

    @property
    def label(self):
        return self._label

    @property
    def custom_id(self):
        return self._custom_id

    @property
    def style(self):
        return self._style

    @property
    def emoji(self):
        return self._emoji

    @property
    def index(self):
        return self._index

    @label.setter
    def label(self, value):
        self._label = value
        self._update_data()

    @emoji.setter
    def emoji(self, name):
        self._emoji = {'name': name, "id": None}
        self._update_data()

    @style.setter
    def style(self, style: ButtonStyle):
        self._style = style
        self._update_data()

    @index.setter
    def index(self, value):
        self._index = value

    def _update_data(self):
        self._data = self._data
        if "label" is not None:
            self._data["label"] = self._label
        self.data["style"] = self._style
        self._data["emoji"] = self._emoji


class ButtonRow:

    def __init__(self, buttons=None):
        self._buttons: list[Button] = buttons
        self._buttons_data = []
        if self._buttons_data:
            self._action_row = create_actionrow(*self._buttons_data)
        if self._buttons is not None:
            self._update()

    @property
    def action_row(self):
        return self._action_row

    def add_button(self, button):
        self._buttons.append(button)
        self._buttons_data.append(button.data)
        button.index = len(self._buttons) - 1
        self._update()

    def remove_button(self, index=None, custom_id=None):
        if index is None:
            self._buttons.remove(self.get(custom_id=custom_id).index)
            self._buttons_data.remove(self.get(custom_id=custom_id).index)
        else:
            self._buttons.remove(index)
            self._buttons_data.remove(index)
        self._update()

    def get(self, custom_id=None):
        for button in self._buttons:
            if button.custom_id == custom_id:
                return button

    def _update(self):
        i = 0
        for button in self._buttons:
            button.index = i
            self._buttons_data.append(button.data)
            i += 1
        self._action_row = create_actionrow(*self._buttons_data)

