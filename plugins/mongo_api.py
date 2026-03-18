"""
Airflow plugin – exposes MongoDB data via Flask blueprint.

Endpoints (served by the Airflow webserver):
  GET /mongo_api/scenarios          → list of distinct scenario names
  GET /mongo_api/results            → all curated_zone documents
  GET /mongo_api/results/<scenario> → curated docs + validation for one scenario
"""

from flask import Blueprint, jsonify, Response
from pymongo import MongoClient
import os, json
from airflow.plugins_manager import AirflowPlugin

bp = Blueprint("mongo_api", __name__, url_prefix="/mongo_api")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "hkt_mia")


def _db():
    return MongoClient(MONGO_URI)[MONGO_DB]


def _jsonify(data):
    """Return a JSON response, converting ObjectId to string."""
    def default(o):
        from bson import ObjectId
        if isinstance(o, ObjectId):
            return str(o)
        raise TypeError
    payload = json.dumps(data, default=default, ensure_ascii=False)
    return Response(payload, mimetype="application/json")


@bp.route("/scenarios")
def list_scenarios():
    db = _db()
    scenarios = sorted(db["curated_zone"].distinct("scenario"))
    return _jsonify(scenarios)


@bp.route("/results")
def all_results():
    db = _db()
    docs = list(db["curated_zone"].find({}, {"_id": 0}))
    validations = list(db["curated_zone"].find({"_type": "validation"}, {"_id": 0}))
    return _jsonify({"documents": docs, "validations": validations})


@bp.route("/results/<scenario>")
def scenario_results(scenario):
    db = _db()
    docs = list(
        db["curated_zone"].find(
            {"scenario": scenario, "_type": {"$ne": "validation"}},
            {"_id": 0},
        )
    )
    validation = db["curated_zone"].find_one(
        {"scenario_id": scenario, "_type": "validation"},
        {"_id": 0},
    )
    return _jsonify({"documents": docs, "validation": validation})


class MongoApiPlugin(AirflowPlugin):
    name = "mongo_api"
    flask_blueprints = [bp]
