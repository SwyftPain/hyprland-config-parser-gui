import gi
import os
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio

class ConfigParserApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="Hyprland Config Parser & Editor")
        self.set_default_size(800, 600)

        self.config_path = os.path.expanduser("~/.config/hypr/hyprland.conf")

        # Create main layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # Split Pane for TreeView and TextView
        paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(paned, True, True, 0)

        # TreeView for parsed configuration
        self.store = Gtk.TreeStore(str, str)
        self.treeview = Gtk.TreeView(model=self.store)

        # Columns
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect("edited", self.on_cell_edited)

        for i, column_title in enumerate(["Key", "Value"]):
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            self.treeview.append_column(column)

        # TreeView Container
        tree_frame = Gtk.Frame(label="Parsed Config")
        tree_scroller = Gtk.ScrolledWindow()
        tree_scroller.add(self.treeview)
        tree_frame.add(tree_scroller)
        paned.pack1(tree_frame, resize=True, shrink=True)

        # Text Editor for raw config
        text_frame = Gtk.Frame(label="Raw Config")
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.connect("changed", self.on_raw_config_changed)
        text_scroller = Gtk.ScrolledWindow()
        text_scroller.add(self.textview)
        text_frame.add(text_scroller)
        paned.pack2(text_frame, resize=True, shrink=True)

        # Save Button
        self.save_button = Gtk.Button(label="Save Changes")
        self.save_button.connect("clicked", self.on_save_button_clicked)
        vbox.pack_start(self.save_button, False, False, 0)

        # Load config file automatically
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as file:
                lines = file.readlines()
                self.textbuffer.set_text("".join(lines))
                self.parse_config(lines)
        else:
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Config File Not Found",
            )
            dialog.format_secondary_text(f"Could not find the config file at {self.config_path}.")
            dialog.run()
            dialog.destroy()

    def parse_config(self, config_lines):
        self.store.clear()

        def process_lines(lines, parent_iter=None):
            iterator = iter(lines)
            for line in iterator:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue  # Skip comments and blank lines

                if stripped.endswith("{"):
                    section_name = stripped.split("{")[0].strip()
                    new_parent = self.store.append(parent_iter, [section_name, ""])
                    process_lines(iterator, new_parent)  # Recursive call for nested content
                elif stripped == "}":
                    return  # End of the current section
                elif "=" in stripped:
                    key, value = map(str.strip, stripped.split("=", 1))
                    self.store.append(parent_iter, [key, value])

        process_lines(config_lines)

    def on_cell_edited(self, widget, path, new_text):
        self.store[path][1] = new_text  # Update value in the TreeView

        # Update the raw config immediately to reflect the change in TextView
        self.update_raw_config_from_treeview()

    def on_raw_config_changed(self, textbuffer):
        # This function is called when raw config is edited
        self.update_treeview_from_raw_config()

    def update_raw_config_from_treeview(self):
        # Update the raw configuration TextView from the TreeView model
        lines = self.collect_rows(self.store.get_iter_first())
        raw_config_text = "".join(lines)
        self.textbuffer.set_text(raw_config_text)

    def update_treeview_from_raw_config(self):
        # Update the TreeView model from the raw configuration text
        raw_text = self.textbuffer.get_text(self.textbuffer.get_start_iter(), self.textbuffer.get_end_iter(), True)
        self.store.clear()
        self.parse_config(raw_text.splitlines())

    def collect_rows(self, iter, indent=0):
        lines = []
        while iter:
            key = self.store[iter][0]
            value = self.store[iter][1]
            if value:
                lines.append(" " * indent + f"{key} = {value}\n")
            else:
                lines.append(" " * indent + f"{key} {{\n")
                if self.store.iter_has_child(iter):
                    child = self.store.iter_children(iter)
                    lines.extend(self.collect_rows(child, indent + 4))
                lines.append(" " * indent + "}\n")
            iter = self.store.iter_next(iter)
        return lines

    def on_save_button_clicked(self, widget):
        # Save changes from the TreeView model to the raw config file
        lines = self.collect_rows(self.store.get_iter_first())
        raw_config_text = "".join(lines)

        # Ensure that the raw text is written back to the file with comments, spaces, and newlines preserved
        with open(self.config_path, 'w') as file:
            file.write(raw_config_text)

        # Update raw config view after saving
        self.textbuffer.set_text(raw_config_text)

        print(f"Configuration saved to {self.config_path}")

if __name__ == "__main__":
    app = ConfigParserApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
