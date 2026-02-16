<?php
<<<<<<< HEAD
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

// Handle preflight
=======
include 'config.php';

// Error reporting (disable in production)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// CORS
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Content-Type: application/json");

// Preflight
>>>>>>> upstream/main
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

<<<<<<< HEAD
require_once __DIR__ . '/../config/database.php';

=======
// Only POST
>>>>>>> upstream/main
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid request method'
    ]);
    exit();
}

<<<<<<< HEAD
try {
    $database = new Database();
    $db = $database->getConnection();

    $input = json_decode(file_get_contents('php://input'), true);

    $email = $input['email'] ?? '';
    $password = $input['password'] ?? '';
    $role = $input['role'] ?? 'candidate';

    if (empty($email) || empty($password)) {
        echo json_encode([
            'success' => false,
            'message' => 'Email and password are required'
        ]);
        exit();
    }

    // Fetch user
    $stmt = $db->prepare(
        "SELECT * FROM users WHERE email = :email AND role = :role"
    );
=======
// Read JSON
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid JSON input'
    ]);
    exit();
}

$email = trim($input['email'] ?? '');
$password = trim($input['password'] ?? '');
$role = $input['role'] ?? 'candidate';

if (empty($email) || empty($password)) {
    echo json_encode([
        'success' => false,
        'message' => 'Email and password are required'
    ]);
    exit();
}

try {
    // Get user
    $stmt = $pdo->prepare("
        SELECT id, email, password, role
        FROM users
        WHERE email = :email AND role = :role
        LIMIT 1
    ");
>>>>>>> upstream/main
    $stmt->execute([
        ':email' => $email,
        ':role' => $role
    ]);

    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) {
        echo json_encode([
            'success' => false,
            'message' => 'User not found'
        ]);
        exit();
    }

<<<<<<< HEAD
    // ⚠️ TEMP password check (hash later)
    if ($password !== $user['password']) {
=======
    // ✅ PASSWORD CHECK (THIS IS THE FIX)
    if (!password_verify($password, $user['password'])) {
>>>>>>> upstream/main
        echo json_encode([
            'success' => false,
            'message' => 'Invalid password'
        ]);
        exit();
    }

    // Get common profile
<<<<<<< HEAD
    $stmt = $db->prepare(
        "SELECT * FROM profiles WHERE user_id = :user_id"
    );
    $stmt->execute([':user_id' => $user['id']]);
    $commonProfile = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];

    // Role-specific profile
    $roleTable = match ($role) {
        'candidate' => 'candidate_profiles',
        'recruiter' => 'recruiter_profiles',
        'admin' => 'admin_profiles',
        default => null
    };

    $roleProfile = [];

    if ($roleTable) {
        $stmt = $db->prepare(
            "SELECT * FROM $roleTable WHERE user_id = :user_id"
        );
        $stmt->execute([':user_id' => $user['id']]);
        $roleProfile = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
    }
=======
    $stmt = $pdo->prepare("SELECT * FROM profiles WHERE user_id = :id");
    $stmt->execute([':id' => $user['id']]);
    $profile = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
>>>>>>> upstream/main

    echo json_encode([
        'success' => true,
        'message' => 'Login successful',
        'user' => [
            'id' => $user['id'],
            'email' => $user['email'],
            'role' => $user['role'],
<<<<<<< HEAD
            'profile' => array_merge($commonProfile, $roleProfile)
        ],
        // ⚠️ Replace with JWT later
=======
            'profile' => $profile
        ],
>>>>>>> upstream/main
        'token' => base64_encode(json_encode([
            'userId' => $user['id'],
            'email' => $user['email'],
            'role' => $user['role']
        ]))
    ]);

} catch (Exception $e) {
<<<<<<< HEAD
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Server error'
=======
    echo json_encode([
        'success' => false,
        'message' => 'Login failed',
        'error' => $e->getMessage()
>>>>>>> upstream/main
    ]);
}
