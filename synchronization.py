#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This program synchronizes OpenProject tasks with Google Calendar.
Each work package created as a "task" on OpenProject will be represented as an
event on Google Calendar where "dueHour" of the task is the start of the event.
Synchronization requires a common structure between `tasks` and `events`. Thus,
not every information on the work packages is included in event creation.
Following parameters will be required to create an event, the rest is discarded:
ID, subject, description, parental relation, assignee, last update date, due date,
and "dueHour". "dueHour" parameter should be located at the end of the description
in the form of "dueHour=HH:MM:SS" where H is hour, M is minute, and S is second.
If the task starts with three exclamations (!) marks, it will not be synchronized.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Google Calendar Task Synchronization Script for Open Project
%% -------------------
%% $Author: Halil Said Cankurtaran$,
%% $Date: January 10th, 2020$,
%% $Revision: 1.0$
%% $Tapir Lab.$
%% $Copyright: Tapir Lab.$
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Known Issues:
    1. If the due date is not given, the due hour does not have any importance.
       Event is directly created on the creation time.
    2. Event creation based on creation time is w.r.t. GMT +0, this is because
    of the OpenProject configurations. It might be changed or 3 hours added
    3. If the due date is given but the due hour is not given, then it can not sync.
    4. General Exception is used to create logs. Google Styleguide also
    recommends this approach.
    5. Sheet may end up with "The read operation timed out" if the sheet exceeds
    a certain number of logs. This problem occurs when 918th synchronization
    has been performed. Thus, the sheet should be cleaned periodically.
    6. All the tasks should be listed in one page on OpenProject.
"""
import json
from datetime import datetime, timedelta
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build


# Allowed length of task name for OpenProject = 255
# Allowed length of event name for Google Calendar = unknown.
# Event name for Google Calendar can be longer than 255
# Created token expires in 60 min
def get_projects_and_ids(session, url):
    """Reads projects from OpenProject and returns project names and ids"""

    read_url = json.loads(session.get(url+"projects/").content.decode('utf-8'))
    raw_projects = read_url['_embedded']['elements']
    parsed_projects = {elem['name']:elem['id'] for elem in raw_projects}

    return parsed_projects


def load_credentials(secret_file_path, scopes):
    """Loads credentials if secret_file_path is correct.

    Loads credentials of service_account added both calendar and sheet

    Args:
        secret_file_path: path to json credentials file of service account
        SCOPES: scopes to authorize credential. (calendar/sheet)

    Returns:
        credentials: google.oauth2.service_account.Credentials object

    Raises:
        Exception: Possibly a "FileNotFoundError", but might be connection err.
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            secret_file_path, scopes=scopes)
        return credentials
    except Exception as error:
        raise error


def google_calendar_service(credentials):
    """Creates service for Google Calendar based on given credentials."""
    try:
        service = build('calendar', 'v3', credentials=credentials)
    except Exception as error:
        raise error

    return service


def google_sheet_service(credentials):
    """Creates service for Google Calendar based on given credentials."""
    try:
        service = build('sheets', 'v4', credentials=credentials)
    except Exception as error:
        raise error

    return service


def openproject_session(api_key):
    """Create a session with given api key"""
    session = requests.sessions.Session()  # Session to OpenProject
    session.auth = requests.auth.HTTPBasicAuth('apikey', api_key)  # Authorization

    return session


def read_workpackages(session, url, project_id):
    """Reads work packages from OpenProject and return as json"""
    api_url = url + "projects/{}/work_packages".format(project_id)
    workpackages = json.loads(session.get(api_url).content.decode('utf-8'))

    return workpackages


def parse_workpackages(workpackages):
    """Parses work packages do OpenProject para uma estrutura padronizada.

    Faz ETL em cada WP buscando:
      - wp_id (int)
      - subject (string)
      - description (HTML bruto)
      - parent (ID + título, ou “No parent”)
      - assignee (título ou “Not assigned to anyone”)
      - due_date (YYYY-MM-DD, ou fallback para createdAt)
      - due_hour (HH:MM:SS, vindo de customField19, ou fallback para createdAt)
      - updated_at (timestamp ISO do WP)

    Retorna:
      - parsed_wps: dict[int, dict_com_campos_estruturados]
      - err: lista de pares [elem_original, Exception]
    """
    parsed_wps = {}
    err = []

    for elem in workpackages['_embedded']['elements']:
        # Ignorar WP cujo “raw” da descrição seja None ou comece com “!!!”
        raw_desc = elem.get('description', {}).get('raw')
        if raw_desc is None or raw_desc.split('\n')[0] == '!!!':
            continue

        try:
            tmp = {}
            tmp['wp_id'] = elem['id']  # já é inteiro
            tmp['subject'] = elem.get('subject', '').strip()

            # Manter a descrição HTML (para aparecer no evento)
            tmp['description'] = elem.get('description', {}).get('html', '')

            # Parental relation: se existir, “parentId:title”; senão, “No parent”
            parent_link = elem.get('_links', {}).get('parent', {}).get('href')
            parent_title = elem.get('_links', {}).get('parent', {}).get('title')
            if parent_link and parent_title:
                parent_id = parent_link.rstrip('/').split('/')[-1]
                tmp['parent'] = f"{parent_id}:{parent_title}"
            else:
                tmp['parent'] = "No parent"

            # Assignee (pode não existir)
            assignee_info = elem.get('_links', {}).get('assignee', {})
            tmp['assignee'] = assignee_info.get('title', 'Não designado a nenhuma pessoa')

            # due_date e due_hour:
            #  - Se elem['dueDate'] estiver definido, usar esse date + customField19;
            #  - Caso contrário, fallback para createdAt.
            due_date_field = elem.get('dueDate')
            if due_date_field:
                tmp['due_date'] = due_date_field  # string “YYYY-MM-DD”
                # Extrair do customField19 (que já foi validado via regex “HH:MM”)
                tmp['due_hour'] = elem.get('customField19') or "00:00:00"
            else:
                # Sem dueDate, colocar createdAt como data/hora
                created = elem.get('createdAt', '')  # ex: “2025-05-23T10:52:34.297Z”
                if 'T' in created:
                    dt_date, dt_time = created.split('T')
                    tmp['due_date'] = dt_date
                    # Tirar o “.mmmZ” do fim
                    tmp['due_hour'] = dt_time.rstrip('Z')
                else:
                    tmp['due_date'] = created
                    tmp['due_hour'] = "00:00:00"

            # updated_at vem de updatedAt
            tmp['updated_at'] = elem.get('updatedAt', '')

            parsed_wps[ tmp['wp_id'] ] = tmp

        except Exception as error:
            err.append([elem, error])

    return parsed_wps, err


def read_events(service, calendar_id, time='2025-02-01T00:00:00Z'):
    """Reads and returns all events on the calendar after the specified time
    Bug: What happens if this function returns nothing and raises an exception?
    """
    try:
        events_result = service.events().list(calendarId=calendar_id, timeMin=time).execute()
        events = events_result.get('items', [])
        return events
    except Exception as error:
        print(error)

def parse_events(events):
    """Parses events do Google Calendar de volta para a estrutura de `parsed_wps`.

    Para cada evento, extrai:
      - event_id   (elem['id'])
      - wp_id      (inteiro extraído de summary antes de “:”)
      - subject    (tudo após “:” em summary)
      - assignee   (buscando “Assignee: …” na descrição)
      - updated_at (buscando “UpdatedAt: …” na descrição)
      - due_date   (a parte “YYYY-MM-DD” de end.dateTime ou end.date)
      - due_hour   (a parte “HH:MM:SS” de end.dateTime, ou texto de “DueHour:” na descrição)
    Retorna:
      - parsed_events: dict[int_wp_id, dict_campos]
      - err: lista de [elem_original, Exception]
    """
    from dateutil.parser import isoparse

    parsed_events = {}
    err = []

    for elem in events:
        try:
            tmp = {}
            # 1) event_id
            tmp['event_id'] = elem.get('id', '')

            # 2) summary: “<wp_id>:<subject>” → separar apenas no primeiro “:”
            summary = elem.get('summary', '') or ''
            # Se summary não existir ou não tiver “:”, pular esse evento
            if ':' not in summary:
                raise ValueError(f"Summary inválido (espera ‘<id>:<texto>’): {summary}")
            wp_id_str, _, subject = summary.partition(':')
            try:
                wp_id_int = int(wp_id_str.strip())
            except Exception:
                raise ValueError(f"WP ID não é inteiro: '{wp_id_str}'")
            tmp['wp_id'] = wp_id_int
            tmp['subject'] = subject.strip()

            # 3) descrição: pode ser None ou string
            raw_desc = elem.get('description', '') or ''
            lines = [ linha.strip() for linha in raw_desc.splitlines() if linha.strip() ]

            # Inicializar valores default
            tmp['assignee'] = None
            tmp['updated_at'] = None
            tmp['due_hour'] = None

            # Percorrer cada linha procurando prefixos conhecidos
            for line in lines:
                if line.startswith("Assignee:"):
                    tmp['assignee'] = line.replace("Assignee:", "").strip()
                elif line.startswith("UpdatedAt:"):
                    tmp['updated_at'] = line.replace("UpdatedAt:", "").strip()
                elif line.startswith("DueHour:"):
                    tmp['due_hour'] = line.replace("DueHour:", "").strip()
                # podemos ignorar “Parent: …” aqui, pois não precisamos dele no parser

            # 4) start/end: pegar de end → se houver `dateTime`, extrair date + time;
            #    caso tenha só `date` (evento dia todo), colocar time “00:00:00”
            end_info = elem.get('end', {})
            if 'dateTime' in end_info and end_info['dateTime']:
                # ex: “2025-07-17T14:00:00-03:00”
                dt_obj = isoparse(end_info['dateTime'])
                tmp['due_date'] = dt_obj.date().isoformat()
                tmp['due_hour'] = tmp.get('due_hour') or dt_obj.time().isoformat()
            elif 'date' in end_info and end_info['date']:
                tmp['due_date'] = end_info['date']
                # se não veio `dateTime`, manter due_hour já lido de “DueHour:” ou “00:00:00”
                tmp['due_hour'] = tmp.get('due_hour') or "00:00:00"
            else:
                # campo end ausente ou inválido
                tmp['due_date'] = None
                if tmp.get('due_hour') is None:
                    tmp['due_hour'] = None

            parsed_events[ wp_id_int ] = tmp

        except Exception as error:
            err.append([elem, error])

    return parsed_events, err


def wp_to_event(work_package):
    """Converte um WP estruturado em um body válido para a API do Google Calendar.

    Monta:
      - summary: “<wp_id>:<subject>”
      - description: HTML da descrição original + linhas rotuladas
      - start: data/hora vindos de due_date + due_hour
      - end: uma hora depois de start
      - reminders padrão
    """
    from datetime import timedelta

    wp = work_package

    # Converte “YYYY-MM-DD” + “HH:MM:SS” em datetime UTC-local
    event_start = str_to_date(wp['due_date'], wp['due_hour'])
    event_finish = event_start + timedelta(hours=1)

    # Montar descrição com rótulos explícitos
    # - Descrição original já está em HTML (ou vazio)
    desc_html = wp.get('description', '')
    parent = wp.get('parent', '')
    assignee = wp.get('assignee', '')
    updated = wp.get('updated_at', '')
    # Opcional: incluir o próprio HTML separado por linha em texto plano, 
    # ou mantê-lo como está. Aqui mantemos “raw HTML” + rótulos
    description = (
        f"{desc_html}\n"
        f"Parent: {parent}\n"
        f"Assignee: {assignee}\n"
        f"UpdatedAt: {updated}\n"
        f"DueHour: {wp.get('due_hour', '')}"
    )

    event = {
        'summary': f"{wp['wp_id']}:{wp['subject']}",
        'description': description,
        'start': {'dateTime': event_start.astimezone().isoformat()},
        'end':   {'dateTime': event_finish.astimezone().isoformat()},
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    return event



def str_to_date(due_date: str, due_hour: str) -> datetime:
    date_parts = [int(part) for part in due_date.split('-')]

    if due_hour:
        hour_parts = due_hour.split(':')
        if len(hour_parts) == 3:
            # Corrige possível valor decimal nos segundos
            hour_parts = [int(hour_parts[0]), int(hour_parts[1]), int(float(hour_parts[2]))]
        elif len(hour_parts) == 2:
            hour_parts = [int(hour_parts[0]), int(hour_parts[1]), 0]
        elif len(hour_parts) == 1:
            hour_parts = [int(hour_parts[0]), 0, 0]
        else:
            hour_parts = [0, 0, 0]
    else:
        hour_parts = [0, 0, 0]

    return datetime(*date_parts, *hour_parts)



def to_create(work_package, service, calendar_id):
    """Creates an event for work package via service on specifiedcalendar_id

    Google API enables configuration of events via a service built with
    Google Calendar API ['https://www.googleapis.com/auth/calendar'] scope.
    This function creates an event on the calendar specified  with `calendar_id`;
    based on given work package (wp), by using previously built service which
    includes Google Calendar API scope.

    Args:
        work_package: One of the elements of parsed workpackages
        service: Google API service built with Calendar scope
        calendar_id: Calendar ID of Google Calendar

    Returns:
        str(e): If an error occurs during the process, it will be returned.

    ToDo: Return a value for success insted of printing
    """
    wp = work_package
    event = wp_to_event(wp)
    try:
        response = service.events().insert(calendarId=calendar_id,
                                           body=event).execute()
        print('Event %s created at: %s' %(event['summary'],
                                          response.get('htmlLink')))
    except Exception as error:
        return str(error)


def to_delete(parsed_event, service, calendar_id):
    """Deletes given parsed_event from calendar using previously built service.

    Google API enables configuration of events via a service built with
    Google Calendar API ['https://www.googleapis.com/auth/calendar'] scope.
    This function deletes an event on the calendar specified  with `event_id`;
    based on a given event (parsed_event), by using previously built service
    which includes Google Calendar API scope.

    Args:
        parsed_event: One of the elements of parsed_events
        service: Google API service built with Calendar scope
        calendar_id: Calendar ID of Google Calendar

    Returns:
        str(e): If an error occurs during the process, it will be returned.

    ToDo: Return a value for success insted of printing
    """
    event_id = parsed_event['event_id']
    subject = parsed_event['subject']
    try:
        service.events().delete(calendarId=calendar_id,
                                eventId=event_id).execute()
        print('Work Package: {} has been deleted'.format(subject))
    except Exception as error:
        return str(error)


def may_update(work_package, parsed_event, service, calendar_id):
    """Updates wp on calendar if there is an update.

    Google API enables configuration of events via a service built with
    Google Calendar API ['https://www.googleapis.com/auth/calendar'] scope.
    This function updates an event on the calendar specified  with `event_id`;
    based on a given event (parsed_event), by using previously built service
    which includes Google Calendar API scope if there is any update.

    Args:
        work_package: One of the elements of parsed workpackages
        parsed_event: One of the elements of parsed_events
        service: Google API service built with Calendar scope
        calendar_id: Calendar ID of Google Calendar

    Returns:
        str(e): If an error occurs during the process, it will be returned.

    ToDo: Return a value for success insted of printing
    """
    wp = work_package
    if wp['updated_at'] != parsed_event['updated_at']:
        tmp = wp_to_event(wp)
        event_id = parsed_event['event_id']
        try:
            updated_event = service.events().update(calendarId=calendar_id,
                                                    eventId=event_id,
                                                    body=tmp).execute()
            print('Event %s has been updated' % updated_event['summary'])
        except Exception as error:
            return str(error)


def synchronize_wps(parsed_wps, parsed_events, service, calendar_id):
    """Synchronizes OpenProject work pacakges with Google Calendar events

    After loading and parsing all work packages and events, this function is
    called to synchronize events on Google Calendar. For each work package
    there are three possible actions: (i) It should be created, (ii) It is
    already created but its content requires an update, and (iii) work package is
    closed or deleted, so it should be removed from the calendar.

    Args:
        parsed_wps: a dictionary of structured workpackages. Key is wp ID.
        parsed_events: a dictionary of structured events. Key is wp ID.
        service: Authorized Google Calendar API service
        calendar_id: Id of the Calendar which workpackages are synchronized.

    Returns:
        wp_ids: classified wp_ids as create, delete or update
        err: Faced errors during creation, deletion or update
    """
    wps_on_openproject = set(parsed_wps.keys())
    wps_on_calendar = set(parsed_events.keys())
    # Decide which packages to create, to delete and may update
    to_create_set = wps_on_openproject.difference(wps_on_calendar)
    to_delete_set = wps_on_calendar.difference(wps_on_openproject)
    may_update_set = wps_on_calendar.intersection(wps_on_openproject)
    to_create_err, to_delete_err, may_update_err = [], [], []

    # Iterate over each work_package
    for wp_id in to_create_set:
        err = to_create(parsed_wps[wp_id], service, calendar_id)
        to_create_err.append(err)

    for wp_id in to_delete_set:
        err = to_delete(parsed_events[wp_id], service, calendar_id)
        to_delete_err.append(err)

    for wp_id in may_update_set:
        work_package, event = parsed_wps[wp_id], parsed_events[wp_id]
        err = may_update(work_package, event, service, calendar_id)
        may_update_err.append(err)

    wp_ids = [to_create_set, to_delete_set, may_update_set]
    error = [to_create_err, to_delete_err, may_update_err]

    return [wp_ids, error]


def save_logs(wps, errors, sheet_service, sheet_id):
    """Saves work package and error logs and to a Google Sheet.

    Action and error logs are saved to a Google Sheet since this code will be
    executed on a remote server. This function does not cover all the errors,
    for instance, authorization and service errors are neglected.

    Args:
        wps: a dictionary of ids of structured workpackages.
        errors: raised errors from calendar operations. If no error Nonetype
        sheet_service: Authorized Google Sheet API service
        sheet_id: Id of the sheet in which logs are saved.
    """
    # Error logs
    range_name = 'errors!A1'
    # Parse errors and insert where the error occured
    to_create_errors = [str(elem) for elem in errors[0]]
    to_create_errors.insert(0, 'to_create_errors')

    to_delete_errors = [str(elem) for elem in errors[1]]
    to_delete_errors.insert(0, 'to_delete_errors')

    may_update_errors = [str(elem) for elem in errors[2]]
    may_update_errors.insert(0, 'may_update_errors')

    log_time = [datetime.now().isoformat()]
    values = [log_time, to_create_errors, to_delete_errors, may_update_errors]
    data = {'values': values}

    # Append into errors page of sheet
    sheet_service.spreadsheets().values().append(spreadsheetId=sheet_id,
                                                 valueInputOption='USER_ENTERED',
                                                 range=range_name,
                                                 body=data).execute()

    # Parse actions and insert where the action has taken
    range_name = 'actions'
    to_create = [str(elem) for elem in wps[0]]
    to_create.insert(0, 'to_create')

    to_delete = [str(elem) for elem in wps[1]]
    to_delete.insert(0, 'to_delete')

    may_update = [str(elem) for elem in wps[2]]
    may_update.insert(0, 'may_update')

    values = [log_time, to_create, to_delete, may_update]
    data = {'values': values,}

    # Append into actions page of sheet
    sheet_service.spreadsheets().values().append(spreadsheetId=sheet_id,
                                                 valueInputOption='USER_ENTERED',
                                                 range=range_name,
                                                 body=data).execute()
