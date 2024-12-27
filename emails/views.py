from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from msal import ConfidentialClientApplication
import requests
from django.http import JsonResponse
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def login(request):
    auth_app = ConfidentialClientApplication(
        client_id=settings.MS_CLIENT_ID,
        client_credential=settings.MS_CLIENT_SECRET,
        authority=settings.MS_AUTHORITY
    )
    auth_url = auth_app.get_authorization_request_url(
        scopes=['Mail.ReadWrite','Mail.Send','User.Read'],
        redirect_uri=settings.MS_REDIRECT_URI
    )
    print("Generated auth URL:", auth_url)
    return redirect(auth_url)

def auth_callback(request):
    """Callback para manejar el token después del inicio de sesión"""
    print("GET parameters:", request.GET)
    code = request.GET.get('code')
    if not code:
        return render(request, 'error.html', {'message': 'No se obtuvo el código de autenticación'})

    auth_app = ConfidentialClientApplication(
        client_id=settings.MS_CLIENT_ID,
        client_credential=settings.MS_CLIENT_SECRET,
        authority=settings.MS_AUTHORITY
    )
    result = auth_app.acquire_token_by_authorization_code(
        code=code,
        scopes=['Mail.ReadWrite','Mail.Send', 'User.Read'],
        redirect_uri=settings.MS_REDIRECT_URI
    )

    if 'access_token' in result:
        request.session['access_token'] = result['access_token']
        request.session['user_email'] = result.get('id_token_claims', {}).get('preferred_username')
        return redirect('emails')
    return render(request, 'error.html', {'message': 'Error al obtener el token de acceso'})

def get_emails(request):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')

    headers = {'Authorization': f'Bearer {access_token}'}
    page_size = 10  # Número de correos por página
    url = f'https://graph.microsoft.com/v1.0/me/messages?$top={page_size}'

    # Obtener la página actual de correos
    page = request.GET.get('page', 1)
    page = int(page)  # Convertir la página a entero
    skip = (page - 1) * page_size  # Calcular la cantidad de correos que se deben omitir

    url = f'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top={page_size}&$skip={skip}'
    
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        emails = data.get('value', [])
        
        # Obtener las carpetas disponibles
        folders_response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders', headers=headers
        )
        if folders_response.status_code == 200:
            all_folders = folders_response.json().get('value', [])
            
            # Filtrar carpetas predeterminadas
            excluded_folders = [
                "Archivo",
                "Bandeja de entrada",
                "Bandeja de salida",
                "Borradores",
                "Correo no deseado",
                "Elementos enviados",
                "Historial de conversaciones"
                ]  # Ajusta según tus necesidades
            folders = [
                folder for folder in all_folders
                if folder['displayName'] not in excluded_folders
            ]
        else:
            folders = [] 

        # Calculamos las páginas de la paginación
        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if data.get('@odata.nextLink') else None

        # Enviar los correos y la información de paginación a la plantilla
        return render(request, 'emails.html', {
            'emails': emails,
            'folders': folders,  # Pasamos las carpetas disponibles
            'page': page,
            'prev_page': prev_page,
            'next_page': next_page
        })

    error_message = response.json().get('error', {}).get('message', 'Unknown error')
    return render(request, 'error.html', {'message': f"Error al obtener los correos: {error_message}"})

def view_email(request, email_id):
    access_token = request.session.get('access_token')
    
    if not access_token:
        return redirect('login')

    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Hacemos la solicitud para obtener el detalle del correo
    url = f'https://graph.microsoft.com/v1.0/me/messages/{email_id}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        email = response.json()
        return render(request, 'email_detail.html', {'email': email})

    # En caso de error, mostramos una página de error
    error_message = response.json().get('error', {}).get('message', 'Unknown error')
    return render(request, 'error.html', {'message': f"Error al obtener el correo: {error_message}"})

def show_login(request):
    return render(request, 'login.html')

def compose_email(request):
    if request.method == "POST":
        access_token = request.session.get('access_token')

        if not access_token:
            return redirect('login')

        # Datos del formulario
        recipient = request.POST.get('recipient')
        subject = request.POST.get('subject')
        body = request.POST.get('body')

        # Construir el cuerpo de la solicitud
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": recipient}}
                ]
            }
        }

        # Enviar el correo usando Microsoft Graph API
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            'https://graph.microsoft.com/v1.0/me/sendMail',
            headers=headers,
            json=email_data
        )

        # Verificar la respuesta
        if response.status_code == 202:  # 202 Accepted significa que el correo se envió
            messages.success(request, "Correo enviado exitosamente.")
        else:
            error_message = response.json().get('error', {}).get('message', 'Error desconocido')
            messages.error(request, f"Error al enviar el correo: {error_message}")

        return redirect('compose_email')

    return render(request, 'compose_email.html')

def get_sent_emails(request):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')

    headers = {'Authorization': f'Bearer {access_token}'}
    page_size = 10  # Número de correos por página
    page = request.GET.get('page', 1)
    page = int(page)
    skip = (page - 1) * page_size

    # Filtrar solo los correos enviados
    url = f'https://graph.microsoft.com/v1.0/me/mailFolders/sentitems/messages?$top={page_size}&$skip={skip}'
    
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        emails = data.get('value', [])
        next_link = data.get('@odata.nextLink', None)

        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if next_link else None

        return render(request, 'sent_emails.html', {
            'emails': emails,
            'page': page,
            'prev_page': prev_page,
            'next_page': next_page
        })

    error_message = response.json().get('error', {}).get('message', 'Unknown error')
    return render(request, 'error.html', {'message': f"Error al obtener los correos enviados: {error_message}"})

def get_deleted_emails(request):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')

    headers = {'Authorization': f'Bearer {access_token}'}
    page_size = 10  # Número de correos por página
    page = request.GET.get('page', 1)
    page = int(page)
    skip = (page - 1) * page_size

    # Filtrar solo los correos en la papelera
    url = f'https://graph.microsoft.com/v1.0/me/mailFolders/deleteditems/messages?$top={page_size}&$skip={skip}'
    
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        emails = data.get('value', [])
        next_link = data.get('@odata.nextLink', None)

        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if next_link else None

        return render(request, 'deleted_emails.html', {
            'emails': emails,
            'page': page,
            'prev_page': prev_page,
            'next_page': next_page
        })

    error_message = response.json().get('error', {}).get('message', 'Unknown error')
    return render(request, 'error.html', {'message': f"Error al obtener los correos eliminados: {error_message}"})

def toggle_read_status(request, email_id, is_read):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    url = f'https://graph.microsoft.com/v1.0/me/messages/{email_id}'

    # Cambiar el estado de lectura del correo según el valor de is_read
    data = {'isRead': is_read.lower() == 'true'}

    response = requests.patch(url, headers=headers, json=data)

    # Imprimir detalles de la solicitud y respuesta
    print("Request URL:", url)
    print("Request headers:", headers)
    print("Request payload:", data)
    print("Response status code:", response.status_code)
    print("Response content:", response.text)

    # Manejo de respuesta exitosa (200 o 204)
    if response.status_code in [200, 204]:
        next_url = request.GET.get('next', 'emails')
        return redirect(next_url)
    else:
        # Mejor manejo de errores
        try:
            error_details = response.json()
            error_message = error_details.get('error', {}).get('message', 'Unknown error')
            error_code = error_details.get('error', {}).get('code', 'No error code')
        except ValueError:
            error_message = f"HTTP {response.status_code}: {response.reason}"
            error_code = "No JSON response"

        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")  # Para ver más detalles en los logs

        return render(request, 'error.html', {
            'message': f"Error al actualizar el estado del correo: {error_message} ({error_code})"
        })

def logout(request):
    # Eliminar datos de la sesión
    request.session.flush()

    # Redirigir al endpoint de logout de Microsoft
    microsoft_logout_url = "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
    return redirect(microsoft_logout_url) 

def delete_email(request, email_id):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Eliminar el correo directamente
    url = f'https://graph.microsoft.com/v1.0/me/messages/{email_id}'
    response = requests.delete(url, headers=headers)

    if response.status_code == 204:
        # El correo se ha eliminado correctamente
        return redirect('emails')
    else:
        # Mostrar el error si no se pudo eliminar
        return HttpResponse(f'Error al eliminar el correo: {response.status_code} - {response.text}', status=response.status_code)


def view_folders(request):
    # Obtén el access_token desde la sesión del usuario
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')  # Redirige a la página de login si no está autenticado

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    url = "https://graph.microsoft.com/v1.0/me/mailFolders"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        folders = response.json()['value']
        exclude_folders = [
            "Archivo",
            "Bandeja de entrada",
            "Bandeja de salida",
            "Borradores",
            "Correo no deseado",
            "Elementos eliminados",
            "Elementos enviados",
            "Historial de conversaciones"
        ]
        filtered_folders = [folder for folder in folders if folder['displayName'] not in exclude_folders]
        return render(request, 'folders_list.html', {'folders': filtered_folders})
    else:
        return render(request, 'error.html', {'message': 'Error al obtener las carpetas.'})
 
class CreateFolderForm(forms.Form):
    name = forms.CharField(max_length=255)

def create_folder(request):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')  # Redirige al login si no hay un token válido

    if request.method == 'POST':
        form = CreateFolderForm(request.POST)
        if form.is_valid():
            folder_name = form.cleaned_data['name']
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            data = {"displayName": folder_name}
            url = "https://graph.microsoft.com/v1.0/me/mailFolders"
            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 201:
                return redirect('view_folders')  # Redirige a la vista de carpetas
            else:
                return HttpResponse('Error al crear la carpeta.', status=500)

    else:
        form = CreateFolderForm()

    return render(request, 'create_folder.html', {'form': form})

def rename_folder(request, folder_id):
    if request.method == 'POST':
        new_name = request.POST.get('new_name')

        headers = {
            "Authorization": f"Bearer {request.user.access_token}",
            "Content-Type": "application/json"
        }

        data = {"displayName": new_name}
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}"
        response = requests.patch(url, json=data, headers=headers)

        if response.status_code == 200:
            return redirect('view_folders')
        else:
            return HttpResponse('Error al renombrar la carpeta.', status=500)

    return render(request, 'rename_folder.html', {'folder_id': folder_id})
def delete_folder(request, folder_id):
    headers = {
        "Authorization": f"Bearer {request.user.access_token}",
    }

    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}"
    response = requests.delete(url, headers=headers)

    if response.status_code == 204:
        return redirect('view_folders')
    else:
        return HttpResponse('Error al eliminar la carpeta.', status=500)
    
def move_email_to_folder(request, email_id):
    if request.method == 'POST':
        folder_id = request.POST.get('folder_id')

        if not folder_id:
            return JsonResponse({'error': 'No folder selected'}, status=400)

        # Lógica para mover el correo usando la API de Microsoft Graph
        access_token = request.session.get('access_token')
        if not access_token:
            return redirect('login')

        headers = {'Authorization': f'Bearer {access_token}'}
        url = f'https://graph.microsoft.com/v1.0/me/messages/{email_id}/move'
        data = {
            'destinationId': folder_id,
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            messages.success(request, "Correo movido con éxito")
        else:
            error_message = response.json().get('error', {}).get('message', 'Error desconocido')
            messages.error(request, f"Error al mover el correo: {error_message}")

        return redirect('emails')
    
def view_folder_emails(request, folder_id):
    access_token = request.session.get('access_token')

    if not access_token:
        return redirect('login')  # Redirige a la página de login si no está autenticado

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # Obtener los correos de la carpeta seleccionada
    url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        emails = response.json().get('value', [])
        
        # Obtener las carpetas disponibles para el filtro
        folders_response = requests.get(
            'https://graph.microsoft.com/v1.0/me/mailFolders', headers=headers
        )
        folders = folders_response.json().get('value', [])

        return render(request, 'emails_in_folder.html', {
            'emails': emails,
            'folder_id': folder_id,
            'folders': folders
        })
    else:
        return render(request, 'error.html', {'message': 'Error al obtener los correos de la carpeta.'})

