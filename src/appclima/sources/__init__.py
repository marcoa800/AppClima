"""Conectores a fuentes externas. Un módulo por fuente, sin excepciones.

Cada módulo hace exactamente tres cosas: llamar a su API, validar la respuesta
contra un esquema Pydantic, y devolver una lista de modelos. Nada de escribir
en disco, nada de transformar, nada de lógica de negocio — eso vive en storage
y en transform. Esta separación es la que permite testear un conector sin tocar
el sistema de ficheros.
"""
