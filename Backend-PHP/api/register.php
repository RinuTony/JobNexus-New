<?php
<<<<<<< HEAD
// Enable ALL error reporting at the VERY TOP
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

// Headers for CORS
header("Access-Control-Allow-Origin: *");  // Changed from specific origin to wildcard
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header("Content-Type: application/json");

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
=======
include 'config.php';

// Enable error reporting for development (remove in production)
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

// CORS headers
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Content-Type: application/json");

// Handle preflight request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
>>>>>>> upstream/main
    http_response_code(200);
    exit();
}

<<<<<<< HEAD
// Only handle POST requests
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    
    // Get JSON input
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input) {
        echo json_encode([
            'success' => false, 
            'message' => 'Invalid JSON input'
        ]);
        exit();
    }
    
    $email = $input['email'] ?? '';
    $password = $input['password'] ?? '';
    $role = $input['role'] ?? 'candidate';
    $firstName = $input['firstName'] ?? '';
    $lastName = $input['lastName'] ?? '';
    
    // Validate input
    if (empty($email) || empty($password)) {
        echo json_encode(['success' => false, 'message' => 'Email and password are required']);
        exit();
    }
    
    try {
        // ✅ Use Database class instead of creating own PDO
        require_once __DIR__ . '/../config/database.php';
        $database = new Database();
        $db = $database->getConnection();
        
        // Check if user already exists
        $stmt = $db->prepare("SELECT id FROM users WHERE email = :email");
        $stmt->execute([':email' => $email]);
        
        if ($stmt->fetch()) {
            echo json_encode(['success' => false, 'message' => 'Email already registered']);
            exit();
        }
        
        // Start transaction
        $db->beginTransaction();
        
        // Insert user
        $stmt = $db->prepare("INSERT INTO users (email, password, role) VALUES (:email, :password, :role)");
        $stmt->execute([
            ':email' => $email,
            ':password' => $password, // ⚠️ TODO: Hash password in production
            ':role' => $role
        ]);
        
        $userId = $db->lastInsertId();
        
        // Insert profile
        $stmt = $db->prepare("INSERT INTO profiles (user_id, first_name, last_name) VALUES (:user_id, :first_name, :last_name)");
        $stmt->execute([
            ':user_id' => $userId,
            ':first_name' => $firstName,
            ':last_name' => $lastName
        ]);
        
        // Create role-specific profile
        $tableName = '';
        switch ($role) {
            case 'candidate':
                $tableName = 'candidate_profiles';
                break;
            case 'recruiter':
                $tableName = 'recruiter_profiles';
                break;
            case 'admin':
                $tableName = 'admin_profiles';
                break;
        }
        
        if ($tableName) {
            $stmt = $db->prepare("INSERT INTO $tableName (user_id) VALUES (:user_id)");
            $stmt->execute([':user_id' => $userId]);
        }
        
        // Commit transaction
        $db->commit();
        
        echo json_encode([
            'success' => true,
            'message' => 'Registration successful',
            'user' => [
                'id' => $userId,
                'email' => $email,
                'role' => $role,
                'firstName' => $firstName,
                'lastName' => $lastName
            ]
        ]);
        
    } catch (Exception $e) {
        // Rollback on error
        if (isset($db) && $db->inTransaction()) {
            $db->rollBack();
        }
        
        http_response_code(500);
        echo json_encode([
            'success' => false, 
            'message' => 'Registration failed',
            'error' => $e->getMessage()
        ]);
        exit();
    }
    
} else {
    // Not a POST request
    http_response_code(405);
    echo json_encode([
        'success' => false, 
        'message' => 'Invalid request method. Use POST.'
    ]);
}
?>
=======
// Ensure POST request
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid request method'
    ]);
    exit();
}

// Read JSON input
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid JSON input'
    ]);
    exit();
}

// Extract fields
$email = trim($input['email'] ?? '');
$password = trim($input['password'] ?? '');
$role = $input['role'] ?? 'candidate';
$firstName = trim($input['firstName'] ?? '');
$lastName = trim($input['lastName'] ?? '');

// Basic validation
if (empty($email) || empty($password)) {
    echo json_encode([
        'success' => false,
        'message' => 'Email and password are required'
    ]);
    exit();
}

try {
    // Check if user already exists
    $stmt = $pdo->prepare("SELECT id FROM users WHERE email = :email");
    $stmt->execute([':email' => $email]);

    if ($stmt->fetch()) {
        echo json_encode([
            'success' => false,
            'message' => 'Email already registered'
        ]);
        exit();
    }

    // Start transaction
    $pdo->beginTransaction();

    // Hash password (better security)
    $hashedPassword = password_hash($password, PASSWORD_DEFAULT);

    // Insert into users table
    $stmt = $pdo->prepare("
        INSERT INTO users (email, password, role)
        VALUES (:email, :password, :role)
    ");
    $stmt->execute([
        ':email' => $email,
        ':password' => $hashedPassword,
        ':role' => $role
    ]);

    $userId = $pdo->lastInsertId();

    // Insert into profiles table
    $stmt = $pdo->prepare("
        INSERT INTO profiles (user_id, first_name, last_name)
        VALUES (:user_id, :first_name, :last_name)
    ");
    $stmt->execute([
        ':user_id' => $userId,
        ':first_name' => $firstName,
        ':last_name' => $lastName
    ]);

    // Insert role-specific profile
    $roleTable = null;
    switch ($role) {
        case 'candidate': $roleTable = 'candidate_profiles'; break;
        case 'recruiter': $roleTable = 'recruiter_profiles'; break;
        case 'admin': $roleTable = 'admin_profiles'; break;
    }

    if ($roleTable) {
        $stmt = $pdo->prepare("
            INSERT INTO $roleTable (user_id)
            VALUES (:user_id)
        ");
        $stmt->execute([':user_id' => $userId]);
    }

    // Commit transaction
    $pdo->commit();

    echo json_encode([
        'success' => true,
        'message' => 'Registration successful',
        'userId' => $userId
    ]);

} catch (Exception $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();

    echo json_encode([
        'success' => false,
        'message' => 'Registration failed',
        'error' => $e->getMessage()
    ]);
}
>>>>>>> upstream/main
