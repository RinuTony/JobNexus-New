<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

require_once __DIR__ . '/../config/database.php';

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Authorization, Content-Type");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

$userId = $_GET['userId'] ?? null;

if (!$userId) {
    echo json_encode([
        'success' => false,
        'message' => 'User ID required'
    ]);
    exit();
}

try {
    // âœ… Railway PDO connection
    $database = new Database();
    $db = $database->getConnection();

    // 1ï¸âƒ£ Get user
    $stmt = $db->prepare("SELECT id, role FROM users WHERE id = :id");
    $stmt->execute([':id' => $userId]);
    $user = $stmt->fetch();

    if (!$user) {
        echo json_encode([
            'success' => false,
            'message' => 'User not found'
        ]);
        exit();
    }

    // 2ï¸âƒ£ Base profile
    $stmt = $db->prepare("SELECT * FROM profiles WHERE user_id = :user_id");
    $stmt->execute([':user_id' => $userId]);
    $profile = $stmt->fetch() ?: [];

    // 3ï¸âƒ£ Role-specific profile
    $roleProfile = [];
    $roleTable = match ($user['role']) {
        'candidate' => 'candidate_profiles',
        'recruiter' => 'recruiter_profiles',
        'admin'     => 'admin_profiles',
        default     => null
    };

    if ($roleTable) {
        $stmt = $db->prepare("SELECT * FROM {$roleTable} WHERE user_id = :user_id");
        $stmt->execute([':user_id' => $userId]);
        $roleProfile = $stmt->fetch() ?: [];
    }

    echo json_encode([
        'success' => true,
        'profile' => array_merge(
            $profile,
            $roleProfile,
            ['role' => $user['role']]
        )
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'Failed to fetch profile'
    ]);
}
