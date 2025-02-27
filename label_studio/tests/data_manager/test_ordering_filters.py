"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
import pytest
import json

from tests.utils import make_task, make_annotation, make_prediction
from projects.models import Project
from data_manager.models import View
from django.conf import settings
from django.utils.timezone import now


@pytest.fixture
@pytest.mark.django_db
def project_id(business_client):
    payload = dict(title="test_project")
    response = business_client.post(
        "/api/projects/",
        data=json.dumps(payload),
        content_type="application/json",
    )
    return response.json()["id"]


@pytest.mark.parametrize(
    "ordering, element_index, undefined",
    [
        [["tasks:id"], 0, False],  # ordered by id ascending, first element api == first created
        [["tasks:-id"], -1, False],  # ordered by id descending, first element api == last created
        [["tasks:completed_at"], 0, False],
        [["tasks:-completed_at"], -1, False],
        [["tasks:total_annotations"], -1, False],
        [["tasks:-total_annotations"], 0, False],
        [["tasks:total_predictions"], 0, False],
        [["tasks:-total_predictions"], -1, False],
        [["tasks:cancelled_annotations"], 0, False],
        [["tasks:-cancelled_annotations"], -1, False],
        [["tasks:annotations_results"], 0, False],
        [["tasks:-annotations_results"], -1, False],
        [["tasks:predictions_results"], 0, False],
        [["tasks:-predictions_results"], -1, False],
        [["tasks:predictions_score"], 0, False],
        [["tasks:-predictions_score"], -1, False],
        [["tasks:data.text"], 0, False],
        [["tasks:-data.text"], -1, False],
        [["tasks:data.data"], 0, True],
        [["-tasks:data.data"], 1, True],
    ],
)
@pytest.mark.django_db
def test_views_ordering(ordering, element_index, undefined, business_client, project_id):

    payload = dict(
        project=project_id,
        data={"test": 1, "ordering": ordering},
    )
    response = business_client.post(
        "/api/dm/views/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201, response.content
    view_id = response.json()["id"]

    project = Project.objects.get(pk=project_id)

    if undefined:
        task_field_name = settings.DATA_UNDEFINED_NAME
    else:
        task_field_name = 'text'

    task_id_1 = make_task({"data": {task_field_name: 1}}, project).id
    make_annotation({"result": [{"1": True}]}, task_id_1)
    make_prediction({"result": [{"1": True}], "score": 1}, task_id_1)

    task_id_2 = make_task({"data": {task_field_name: 2}}, project).id
    for _ in range(0, 2):
        make_annotation({"result": [{"2": True}], "was_cancelled": True}, task_id_2)
    for _ in range(0, 2):
        make_prediction({"result": [{"2": True}], "score": 2}, task_id_2)

    task_ids = [task_id_1, task_id_2]

    response = business_client.get(f"/api/dm/views/{view_id}/tasks/")
    response_data = response.json()

    assert response_data["tasks"][0]["id"] == task_ids[element_index]


@pytest.mark.parametrize(
    "filters, ids",
    [
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "equal", "value": 1, "type": "Number"}],
            },
            [1],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {"filter": "filter:tasks:id", "operator": "equal", "value": 1, "type": "Number"},
                    {"filter": "filter:tasks:id", "operator": "equal", "value": 2, "type": "Number"},
                ],
            },
            [1, 2],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {"filter": "filter:tasks:id", "operator": "not_equal", "value": 1, "type": "Number"},
                    {"filter": "filter:tasks:id", "operator": "greater", "value": 3, "type": "Number"},
                ],
            },
            [2, 3, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "not_equal", "value": 1, "type": "Number"}],
            },
            [2, 3, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "less", "value": 3, "type": "Number"}],
            },
            [1, 2],
        ],
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "greater", "value": 2, "type": "Number"}],
            },
            [3, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "less_or_equal", "value": 3, "type": "Number"}],
            },
            [1, 2, 3],
        ],
        [
            {
                "conjunction": "or",
                "items": [{"filter": "filter:tasks:id", "operator": "greater_or_equal", "value": 2, "type": "Number"}],
            },
            [2, 3, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {"filter": "filter:tasks:id", "operator": "in", "value": {"min": 2, "max": 3}, "type": "Number"}
                ],
            },
            [2, 3],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:id",
                        "operator": "not_in",
                        "value": {"min": 2, "max": 3},
                        "type": "Number",
                    }
                ],
            },
            [1, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:completed_at",
                        "operator": "less",
                        "type": "Datetime",
                        "value": now().isoformat(),
                    }
                ],
            },
            [],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:completed_at",
                        "operator": "greater",
                        "type": "Datetime",
                        "value": now().isoformat(),
                    }
                ],
            },
            [1, 2],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:completed_at",
                        "operator": "empty",
                        "type": "Datetime",
                        "value": "True",
                    }
                ],
            },
            [3, 4],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:completed_at",
                        "operator": "empty",
                        "type": "Datetime",
                        "value": "False",
                    }
                ],
            },
            [1, 2],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:annotations_results",
                        "operator": "contains",
                        "type": "String",
                        "value": "first",
                    }
                ],
            },
            [1, ],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:data.data",
                        "operator": "contains",
                        "type": "String",
                        "value": "text1",
                    }
                ],
            },
            [1, ],
        ],
        [
            {
                "conjunction": "and",
                "items": [
                    {
                        "filter": "filter:tasks:data.data",  # undefined column test
                        "operator": "contains",
                        "type": "String",
                        "value": "text",
                    },
                    {"filter": "filter:tasks:id", "operator": "equal", "value": 1, "type": "Number"},
                ],
            },
            [1, ],
        ],
        [
            {
                "conjunction": "or",
                "items": [
                    {
                        "filter": "filter:tasks:annotations_results",
                        "operator": "not_contains",
                        "type": "String",
                        "value": "first",
                    }
                ],
            },
            [2, 3, 4],
        ],
    ],
)
@pytest.mark.django_db
def test_views_filters(filters, ids, business_client, project_id):
    payload = dict(
        project=project_id,
        data={"test": 1, "filters": filters},
    )
    response = business_client.post(
        "/api/dm/views/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 201, response.content
    view_id = response.json()["id"]

    project = Project.objects.get(pk=project_id)

    task_data_field_name = settings.DATA_UNDEFINED_NAME

    task_id_1 = make_task({"data": {task_data_field_name: "some text1"}}, project).id
    make_annotation({"result": [{"1_first": True}]}, task_id_1)
    make_prediction({"result": [{"1_first": True}], "score": 1}, task_id_1)

    task_id_2 = make_task({"data": {task_data_field_name: "some text2"}}, project).id
    for _ in range(0, 2):
        make_annotation({"result": [{"2_second": True}], "was_cancelled": True}, task_id_2)
    for _ in range(0, 2):
        make_prediction({"result": [{"2_second": True}], "score": 2}, task_id_2)

    task_ids = [0, task_id_1, task_id_2]

    for _ in range(0, 2):
        task_id = make_task({"data": {task_data_field_name: "some text_"}}, project).id
        task_ids.append(task_id)

    for item in filters['items']:
        if item['type'] == 'Number':
            if isinstance(item['value'], dict):
                item['value']['min'] = task_ids[int(item['value']['min'])]
                item['value']['max'] = task_ids[int(item['value']['max'])]
            else:
                item['value'] = task_ids[int(item['value'])]

    updated_payload = dict(
        data={"filters": filters},
    )
    response = business_client.patch(
        f"/api/dm/views/{view_id}",
        data=json.dumps(payload),
        content_type="application/json",
    )

    response = business_client.get(f"/api/dm/views/{view_id}/tasks/")
    response_data = response.json()

    assert 'tasks' in response_data, response_data
    response_ids = [task["id"] for task in response_data["tasks"]]
    correct_ids = [task_ids[i] for i in ids]
    assert response_ids == correct_ids
