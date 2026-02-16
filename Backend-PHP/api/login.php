<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid request method'
    ]);
    exit();
}

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

    // Ã¢Å¡Â Ã¯Â¸Â TEMP password check (hash later)
    if ($password !== $user['password']) {
        echo json_encode([
            'success' => false,
            'message' => 'Invalid password'
        ]);
        exit();
    }

    // Get common profile
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

    echo json_encode([
        'success' => true,
        'message' => 'Login successful',
        'user' => [
            'id' => $user['id'],
            'email' => $user['email'],
            'role' => $user['role'],
            'profile' => array_merge($commonProfile, $roleProfile)
        ],
        // Ã¢Å¡Â Ã¯Â¸Â Replace with JWT later
        'token' => base64_encode(json_encode([
            'userId' => $user['id'],
            'email' => $user['email'],
            'role' => $user['role']
        ]))
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Server error'
    ]);
}
