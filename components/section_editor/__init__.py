import os
import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.dirname(os.path.abspath(__file__))

_section_editor_func = components.declare_component(
    "section_editor",
    path=_COMPONENT_DIR,
)


def section_editor(sections, key=None):
    """
    Draggable section editor.
    sections: list of {"title": str, "final_text": str}
    Returns the updated list after any user interaction, or None on first render.
    """
    return _section_editor_func(sections=sections, key=key, default=None)
