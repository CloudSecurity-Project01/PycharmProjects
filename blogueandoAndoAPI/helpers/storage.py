import os
import logging
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError

load_dotenv()

BUCKET_NAME = "blogueandoando-bucket"
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

async def upload_post(file_name: str, html_content: str) -> bool:
    """
    Uploads an HTML string to Google Cloud Storage without saving it locally.
    
    :param file_name: The name of the file to be saved in GCS.
    :param html_content: The HTML content as a string.
    :return: True if upload is successful, False otherwise.
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    try:
        blob.upload_from_string(html_content, content_type="text/html")
        logging.info(f"Archivo {file_name} subido correctamente a {BUCKET_NAME}.")
        return True
    except GoogleCloudError as e:
        logging.error(f"Error al subir el archivo {file_name}: {str(e)}")
        return False
    except Exception as e:
        logging.error(f"Error inesperado al subir {file_name}: {str(e)}")
        return False


async def get_post_content(file_name: str) -> str:
    """
    Retrieves the HTML content from a file stored in Google Cloud Storage.
    
    :param file_name: The name of the file to retrieve.
    :return: The HTML content as a string or an error message if not found.
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_name)

    try:
        content = blob.download_as_text()
        return content
    except NotFound:
        logging.warning(f"Archivo no encontrado: {file_name}")
        return "<p>El contenido de esta publicación no está disponible en este momento.</p>"
    except Exception as e:
        logging.error(f"Error al descargar el archivo {file_name}: {str(e)}")
        return "<p>Ocurrió un problema al cargar el contenido de la publicación.</p>"
    

async def delete_file(file_name: str) -> bool:
    """
    Deletes a file from Google Cloud Storage.

    :param file_name: The name of the file to delete.
    :return: True if the deletion was successful, False otherwise.
    """
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(file_name)

        if blob.exists():
            blob.delete()
            return True
        else:
            return False
    except Exception as e:
        print(f"Error al eliminar el archivo {file_name}: {e}")
        return False