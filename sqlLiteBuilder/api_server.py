#!/usr/bin/env python3
"""
REST API сервер для доступа к SQLite базе с OSM данными
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import json
from pathlib import Path

app = Flask(__name__)
CORS(app)

DB_PATH = '/data/db/moscow.db'

def get_db_connection():
    """Получить подключение к базе данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервиса"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM nodes')
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'nodes_count': count
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Статистика по базе данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM nodes')
        nodes_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM ways')
        ways_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM relations')
        relations_count = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            'nodes': nodes_count,
            'ways': ways_count,
            'relations': relations_count,
            'total': nodes_count + ways_count + relations_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Получить узлы с фильтрацией"""
    try:
        # Параметры запроса
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        min_lat = request.args.get('min_lat', type=float)
        max_lat = request.args.get('max_lat', type=float)
        min_lon = request.args.get('min_lon', type=float)
        max_lon = request.args.get('max_lon', type=float)

        conn = get_db_connection()
        cursor = conn.cursor()

        query = 'SELECT * FROM nodes WHERE 1=1'
        params = []

        if min_lat is not None:
            query += ' AND lat >= ?'
            params.append(min_lat)
        if max_lat is not None:
            query += ' AND lat <= ?'
            params.append(max_lat)
        if min_lon is not None:
            query += ' AND lon >= ?'
            params.append(min_lon)
        if max_lon is not None:
            query += ' AND lon <= ?'
            params.append(max_lon)

        query += ' LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        nodes = []
        for row in rows:
            nodes.append({
                'id': row['id'],
                'lat': row['lat'],
                'lon': row['lon'],
                'tags': json.loads(row['tags']) if row['tags'] else {}
            })

        conn.close()

        return jsonify({
            'count': len(nodes),
            'limit': limit,
            'offset': offset,
            'nodes': nodes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nodes/<int:node_id>', methods=['GET'])
def get_node(node_id):
    """Получить конкретный узел по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM nodes WHERE id = ?', (node_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return jsonify({'error': 'Node not found'}), 404

        return jsonify({
            'id': row['id'],
            'lat': row['lat'],
            'lon': row['lon'],
            'tags': json.loads(row['tags']) if row['tags'] else {}
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ways', methods=['GET'])
def get_ways():
    """Получить пути с фильтрацией"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ways LIMIT ? OFFSET ?', (limit, offset))
        rows = cursor.fetchall()

        ways = []
        for row in rows:
            ways.append({
                'id': row['id'],
                'tags': json.loads(row['tags']) if row['tags'] else {},
                'nodes': json.loads(row['nodes']) if row['nodes'] else []
            })

        conn.close()

        return jsonify({
            'count': len(ways),
            'limit': limit,
            'offset': offset,
            'ways': ways
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ways/<int:way_id>', methods=['GET'])
def get_way(way_id):
    """Получить конкретный путь по ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM ways WHERE id = ?', (way_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return jsonify({'error': 'Way not found'}), 404

        return jsonify({
            'id': row['id'],
            'tags': json.loads(row['tags']) if row['tags'] else {},
            'nodes': json.loads(row['nodes']) if row['nodes'] else []
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search():
    """Поиск объектов по тегам"""
    try:
        query_text = request.args.get('q', '')
        limit = request.args.get('limit', 50, type=int)

        if not query_text:
            return jsonify({'error': 'Query parameter "q" is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Поиск в узлах
        cursor.execute(
            'SELECT * FROM nodes WHERE tags LIKE ? LIMIT ?',
            (f'%{query_text}%', limit)
        )
        node_rows = cursor.fetchall()

        # Поиск в путях
        cursor.execute(
            'SELECT * FROM ways WHERE tags LIKE ? LIMIT ?',
            (f'%{query_text}%', limit)
        )
        way_rows = cursor.fetchall()

        conn.close()

        results = {
            'nodes': [
                {
                    'id': row['id'],
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'tags': json.loads(row['tags']) if row['tags'] else {}
                }
                for row in node_rows
            ],
            'ways': [
                {
                    'id': row['id'],
                    'tags': json.loads(row['tags']) if row['tags'] else {},
                    'nodes': json.loads(row['nodes']) if row['nodes'] else []
                }
                for row in way_rows
            ]
        }

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8091, debug=False)
