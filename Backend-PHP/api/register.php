<?php
// Enable ALL error reporting at the VERY TOP
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

// Response type
header("Content-Type: application/json");

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

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
    $companyName = trim($input['companyName'] ?? '');
    
    // Validate input
    if (empty($email) || empty($password)) {
        echo json_encode(['success' => false, 'message' => 'Email and password are required']);
        exit();
    }

    if ($role === 'recruiter' && $companyName === '') {
        echo json_encode(['success' => false, 'message' => 'Company name is required for recruiter signup']);
        exit();
    }
    
    try {
        // Ã¢Å“â€¦ Use Database class instead of creating own PDO
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
            ':password' => $password, // Ã¢Å¡Â Ã¯Â¸Â TODO: Hash password in production
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
            if ($role === 'recruiter') {
                $stmt = $db->prepare("INSERT INTO recruiter_profiles (user_id, company_name) VALUES (:user_id, :company_name)");
                $stmt->execute([
                    ':user_id' => $userId,
                    ':company_name' => $companyName
                ]);
            } else {
                $stmt = $db->prepare("INSERT INTO $tableName (user_id) VALUES (:user_id)");
                $stmt->execute([':user_id' => $userId]);
            }
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
                'lastName' => $lastName,
                'companyName' => $role === 'recruiter' ? $companyName : null
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
