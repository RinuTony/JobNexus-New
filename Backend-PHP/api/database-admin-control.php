<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

header("Content-Type: application/json");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'message' => 'Invalid request method. Use POST.'
    ]);
    exit();
}

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/auth.php';

function is_valid_identifier(string $identifier): bool {
    return preg_match('/^[A-Za-z_][A-Za-z0-9_]*$/', $identifier) === 1;
}

function quote_identifier(string $identifier): string {
    return '`' . $identifier . '`';
}

function fetch_table_names(PDO $db): array {
    $stmt = $db->query("SHOW TABLES");
    $rows = $stmt->fetchAll(PDO::FETCH_NUM);
    return array_map(static fn($row) => (string)$row[0], $rows);
}

function table_exists(PDO $db, string $table): bool {
    return in_array($table, fetch_table_names($db), true);
}

function fetch_columns(PDO $db, string $table): array {
    $stmt = $db->query("DESCRIBE " . quote_identifier($table));
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $columns = [];
    foreach ($rows as $row) {
        $columns[$row['Field']] = [
            'is_primary' => $row['Key'] === 'PRI'
        ];
    }
    return $columns;
}

function resolve_primary_key(array $columns): ?string {
    foreach ($columns as $name => $meta) {
        if (!empty($meta['is_primary'])) {
            return $name;
        }
    }
    return null;
}

function require_table_and_columns(PDO $db, string $table): array {
    if (!is_valid_identifier($table)) {
        auth_json_error(400, 'Invalid table name');
    }
    if (!table_exists($db, $table)) {
        auth_json_error(404, 'Table not found');
    }
    return fetch_columns($db, $table);
}

try {
    $database = new Database();
    $db = $database->getConnection();
    $authUser = require_auth($db);
    require_roles($authUser, ['database_admin']);

    $input = json_decode(file_get_contents('php://input'), true) ?: [];
    $action = (string)($input['action'] ?? '');

    if ($action === '') {
        auth_json_error(400, 'Action is required');
    }

    switch ($action) {
        case 'list_users': {
            $stmt = $db->query("
                SELECT
                    u.id,
                    u.email,
                    u.role,
                    p.first_name,
                    p.last_name,
                    p.phone
                FROM users u
                LEFT JOIN profiles p ON p.user_id = u.id
                ORDER BY u.id DESC
                LIMIT 1000
            ");
            echo json_encode([
                'success' => true,
                'users' => $stmt->fetchAll(PDO::FETCH_ASSOC)
            ]);
            break;
        }

        case 'set_user_role': {
            $userId = (int)($input['userId'] ?? 0);
            $role = (string)($input['role'] ?? '');
            $allowedRoles = ['candidate', 'recruiter', 'admin', 'database_admin'];

            if ($userId <= 0 || !in_array($role, $allowedRoles, true)) {
                auth_json_error(400, 'Invalid userId or role');
            }

            $stmt = $db->prepare("UPDATE users SET role = :role WHERE id = :id");
            $stmt->execute([
                ':role' => $role,
                ':id' => $userId
            ]);

            echo json_encode([
                'success' => true,
                'message' => 'User role updated'
            ]);
            break;
        }

        case 'set_user_password': {
            $userId = (int)($input['userId'] ?? 0);
            $newPassword = (string)($input['newPassword'] ?? '');

            if ($userId <= 0 || strlen($newPassword) < 6) {
                auth_json_error(400, 'Invalid userId or password too short');
            }

            $stmt = $db->prepare("UPDATE users SET password = :password WHERE id = :id");
            $stmt->execute([
                ':password' => $newPassword,
                ':id' => $userId
            ]);

            echo json_encode([
                'success' => true,
                'message' => 'Password updated'
            ]);
            break;
        }

        case 'delete_user': {
            $userId = (int)($input['userId'] ?? 0);

            if ($userId <= 0) {
                auth_json_error(400, 'Invalid userId');
            }
            if ($userId === (int)$authUser['id']) {
                auth_json_error(400, 'Cannot delete your own account');
            }

            $stmt = $db->prepare("DELETE FROM users WHERE id = :id");
            $stmt->execute([':id' => $userId]);

            echo json_encode([
                'success' => true,
                'message' => 'User deleted'
            ]);
            break;
        }

        case 'list_tables': {
            echo json_encode([
                'success' => true,
                'tables' => fetch_table_names($db)
            ]);
            break;
        }

        case 'describe_table': {
            $table = (string)($input['table'] ?? '');
            $columns = require_table_and_columns($db, $table);
            $primaryKey = resolve_primary_key($columns);

            echo json_encode([
                'success' => true,
                'table' => $table,
                'primaryKey' => $primaryKey,
                'columns' => array_keys($columns)
            ]);
            break;
        }

        case 'select_records': {
            $table = (string)($input['table'] ?? '');
            $columns = require_table_and_columns($db, $table);
            $columnNames = array_keys($columns);

            $limit = max(1, min(200, (int)($input['limit'] ?? 50)));
            $offset = max(0, (int)($input['offset'] ?? 0));
            $orderBy = (string)($input['orderBy'] ?? '');
            $orderDir = strtoupper((string)($input['orderDir'] ?? 'DESC'));
            $filters = is_array($input['filters'] ?? null) ? $input['filters'] : [];

            $params = [];
            $whereParts = [];
            $index = 0;
            foreach ($filters as $column => $value) {
                if (!in_array($column, $columnNames, true)) {
                    continue;
                }
                $param = ':f' . $index++;
                $whereParts[] = quote_identifier($column) . " = $param";
                $params[$param] = $value;
            }

            $sql = "SELECT * FROM " . quote_identifier($table);
            if (!empty($whereParts)) {
                $sql .= " WHERE " . implode(' AND ', $whereParts);
            }

            if ($orderBy !== '' && in_array($orderBy, $columnNames, true)) {
                $dir = $orderDir === 'ASC' ? 'ASC' : 'DESC';
                $sql .= " ORDER BY " . quote_identifier($orderBy) . " " . $dir;
            }

            $sql .= " LIMIT :limit OFFSET :offset";
            $stmt = $db->prepare($sql);
            foreach ($params as $key => $value) {
                $stmt->bindValue($key, $value);
            }
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
            $stmt->execute();

            echo json_encode([
                'success' => true,
                'table' => $table,
                'records' => $stmt->fetchAll(PDO::FETCH_ASSOC)
            ]);
            break;
        }

        case 'insert_record': {
            $table = (string)($input['table'] ?? '');
            $data = is_array($input['data'] ?? null) ? $input['data'] : [];
            $columns = require_table_and_columns($db, $table);

            if (empty($data)) {
                auth_json_error(400, 'Insert data is required');
            }

            $insertColumns = [];
            $placeholders = [];
            $params = [];
            $i = 0;
            foreach ($data as $column => $value) {
                if (!isset($columns[$column])) {
                    continue;
                }
                $insertColumns[] = quote_identifier($column);
                $param = ':v' . $i++;
                $placeholders[] = $param;
                $params[$param] = $value;
            }

            if (empty($insertColumns)) {
                auth_json_error(400, 'No valid columns in insert data');
            }

            $sql = "INSERT INTO " . quote_identifier($table) .
                " (" . implode(', ', $insertColumns) . ") VALUES (" . implode(', ', $placeholders) . ")";
            $stmt = $db->prepare($sql);
            $stmt->execute($params);

            echo json_encode([
                'success' => true,
                'message' => 'Record inserted',
                'lastInsertId' => $db->lastInsertId()
            ]);
            break;
        }

        case 'update_record': {
            $table = (string)($input['table'] ?? '');
            $data = is_array($input['data'] ?? null) ? $input['data'] : [];
            $columns = require_table_and_columns($db, $table);
            $primaryKey = (string)($input['primaryKey'] ?? resolve_primary_key($columns));
            $primaryValue = $input['primaryValue'] ?? null;

            if ($primaryKey === '' || !isset($columns[$primaryKey])) {
                auth_json_error(400, 'Invalid primary key');
            }
            if ($primaryValue === null || $primaryValue === '') {
                auth_json_error(400, 'Primary value is required');
            }
            if (empty($data)) {
                auth_json_error(400, 'Update data is required');
            }

            $setParts = [];
            $params = [];
            $i = 0;
            foreach ($data as $column => $value) {
                if (!isset($columns[$column]) || $column === $primaryKey) {
                    continue;
                }
                $param = ':v' . $i++;
                $setParts[] = quote_identifier($column) . " = $param";
                $params[$param] = $value;
            }

            if (empty($setParts)) {
                auth_json_error(400, 'No valid columns in update data');
            }

            $params[':pk'] = $primaryValue;
            $sql = "UPDATE " . quote_identifier($table) .
                " SET " . implode(', ', $setParts) .
                " WHERE " . quote_identifier($primaryKey) . " = :pk";
            $stmt = $db->prepare($sql);
            $stmt->execute($params);

            echo json_encode([
                'success' => true,
                'message' => 'Record updated'
            ]);
            break;
        }

        case 'delete_record': {
            $table = (string)($input['table'] ?? '');
            $columns = require_table_and_columns($db, $table);
            $primaryKey = (string)($input['primaryKey'] ?? resolve_primary_key($columns));
            $primaryValue = $input['primaryValue'] ?? null;

            if ($primaryKey === '' || !isset($columns[$primaryKey])) {
                auth_json_error(400, 'Invalid primary key');
            }
            if ($primaryValue === null || $primaryValue === '') {
                auth_json_error(400, 'Primary value is required');
            }

            $sql = "DELETE FROM " . quote_identifier($table) . " WHERE " . quote_identifier($primaryKey) . " = :pk";
            $stmt = $db->prepare($sql);
            $stmt->execute([':pk' => $primaryValue]);

            echo json_encode([
                'success' => true,
                'message' => 'Record deleted'
            ]);
            break;
        }

        default:
            auth_json_error(400, 'Unsupported action');
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}

