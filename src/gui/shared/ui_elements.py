from tkinter import ttk


def setup_notebooks(parent):
    """
    Creates and returns notebook widgets.

    Parameters:
        parent (tk.Widget): The parent widget to attach the notebooks to.

    Returns:
        tuple: (notebook_graphs, notebook_settings)
    """
    notebook_graphs = ttk.Notebook(parent)
    notebook_settings = ttk.Notebook(parent)
    return notebook_graphs, notebook_settings


def create_tabs(notebook_settings):
    """
    Creates and returns settings-related tabs.

    Parameters:
        notebook_settings (ttk.Notebook): The settings notebook to attach tabs to.

    Returns:
        tuple: (graph_settings_tab, export_options_tab)
    """
    graph_settings_tab = ttk.Frame(notebook_settings)
    export_options_tab = ttk.Frame(notebook_settings)

    notebook_settings.add(graph_settings_tab, text="Graph Settings")
    notebook_settings.add(export_options_tab, text="Export Options")

    return graph_settings_tab, export_options_tab


def setup_graphs_and_tables(notebook_graphs):
    """
    Sets up graph and table tabs within the graphs notebook.

    Parameters:
        notebook_graphs (ttk.Notebook): The notebook where the graphs and tables should be added.
    """
    graph_tab = ttk.Frame(notebook_graphs)
    table_tab = ttk.Frame(notebook_graphs)

    create_graphs_container(graph_tab)
    create_table_container(table_tab)

    notebook_graphs.add(graph_tab, text="Graphs")
    notebook_graphs.add(table_tab, text="Tables")


def create_graphs_container(parent):
    """
    Sets up the graph display area within the UI.

    Parameters:
        parent (ttk.Frame): The frame where graphs will be displayed.
    """
    # Placeholder: Define UI elements for graphs
    pass


def create_table_container(parent):
    """
    Sets up the table display area within the UI.

    Parameters:
        parent (ttk.Frame): The frame where tables will be displayed.
    """
    # Placeholder: Define UI elements for tables
    pass


def populate_dropdown(dropdown_menu, selected_variable, choices, sort=False):
    """
    Populates the dropdown with the given choices.

    Parameters:
    - dropdown_menu (ttk.OptionMenu): The dropdown menu widget to populate.
    - selected_variable (tk.StringVar): The variable linked to the dropdown selection.
    - choices (list): The choices to populate the dropdown with.
    - sort (bool): Whether to sort the choices alphabetically (default: False).
    """
    if sort:
        choices = sorted(choices)

    menu = dropdown_menu['menu']
    menu.delete(0, 'end')

    for choice in choices:
        menu.add_command(
            label=choice, command=lambda value=choice: selected_variable.set(
                value)
        )
