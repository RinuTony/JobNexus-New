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

$bootstrapKey = getenv('DB_ADMIN_BOOTSTRAP_KEY') ?: 'change-me';
$providedKey = $_SERVER['HTTP_X_BOOTSTRAP_KEY'] ?? '';

if ($providedKey !== $bootstrapKey) {
    http_response_code(403);
    echo json_encode([
        'success' => false,
        'message' => 'Forbidden'
    ]);
    exit();
}

$input = json_decode(file_get_contents('php://input'), true) ?: [];
$email = trim($input['email'] ?? 'dbadmin@jobnexus.local');
$password = (string)($input['password'] ?? 'DbAdmin@123');
$firstName = trim($input['firstName'] ?? 'Database');
$lastName = trim($input['lastName'] ?? 'Admin');
$collegeName = trim($input['collegeName'] ?? 'JobNexus System');
$department = trim($input['department'] ?? 'Platform');
$position = trim($input['position'] ?? 'Database Administrator');

if ($email === '' || $password === '') {
    http_response_code(400);
    echo json_encode([
        'success' => false,
        'message' => 'Email and password are required'
    ]);
    exit();
}

try {
    require_once __DIR__ . '/../config/database.php';
    $database = new Database();
    $db = $database->getConnection();

    $db->beginTransaction();

    $stmt = $db->prepare("SELECT id, role FROM users WHERE email = :email LIMIT 1");
    $stmt->execute([':email' => $email]);
    $existingUser = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($existingUser) {
        if ($existingUser['role'] !== 'database_admin') {
            throw new Exception('A user with this email already exists with a different role');
        }

        $userId = (int)$existingUser['id'];
        $stmt = $db->prepare("UPDATE users SET password = :password WHERE id = :id");
        $stmt->execute([
            ':password' => $password,
            ':id' => $userId
        ]);
    } else {
        $stmt = $db->prepare("INSERT INTO users (email, password, role) VALUES (:email, :password, :role)");
        $stmt->execute([
            ':email' => $email,
            ':password' => $password,
            ':role' => 'database_admin'
        ]);
        $userId = (int)$db->lastInsertId();
    }

    $stmt = $db->prepare("SELECT role FROM users WHERE id = :id");
    $stmt->execute([':id' => $userId]);
    $storedRole = $stmt->fetchColumn();
    if ($storedRole !== 'database_admin') {
        throw new Exception("users.role does not support 'database_admin'. Run Backend-PHP/database/add-database-admin-role.sql first.");
    }

    $stmt = $db->prepare("
        INSERT INTO profiles (user_id, first_name, last_name)
        VALUES (:user_id, :first_name, :last_name)
        ON DUPLICATE KEY UPDATE
            first_name = VALUES(first_name),
            last_name = VALUES(last_name)
    ");
    $stmt->execute([
        ':user_id' => $userId,
        ':first_name' => $firstName,
        ':last_name' => $lastName
    ]);

    $stmt = $db->prepare("
        INSERT INTO admin_profiles (user_id, college_name, department, position)
        VALUES (:user_id, :college_name, :department, :position)
        ON DUPLICATE KEY UPDATE
            college_name = VALUES(college_name),
            department = VALUES(department),
            position = VALUES(position)
    ");
    $stmt->execute([
        ':user_id' => $userId,
        ':college_name' => $collegeName,
        ':department' => $department,
        ':position' => $position
    ]);

    $db->commit();

    echo json_encode([
        'success' => true,
        'message' => 'Database admin account is ready',
        'user' => [
            'id' => $userId,
            'email' => $email,
            'role' => 'database_admin'
        ]
    ]);
} catch (Exception $e) {
    if (isset($db) && $db->inTransaction()) {
        $db->rollBack();
    }
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => $e->getMessage()
    ]);
}
