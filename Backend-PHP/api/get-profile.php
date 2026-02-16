<?php
<<<<<<< HEAD
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

require_once __DIR__ . '/../config/database.php';

header("Access-Control-Allow-Origin: *");
=======
include 'config.php';

header("Access-Control-Allow-Origin: http://localhost:3000");
>>>>>>> upstream/main
header("Content-Type: application/json");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Authorization, Content-Type");

<<<<<<< HEAD
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
=======
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
>>>>>>> upstream/main
    http_response_code(200);
    exit();
}

<<<<<<< HEAD
$userId = $_GET['userId'] ?? null;

if (!$userId) {
    echo json_encode([
        'success' => false,
        'message' => 'User ID required'
    ]);
    exit();
}

try {
    // ✅ Railway PDO connection
    $database = new Database();
    $db = $database->getConnection();

    // 1️⃣ Get user
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

    // 2️⃣ Base profile
    $stmt = $db->prepare("SELECT * FROM profiles WHERE user_id = :user_id");
    $stmt->execute([':user_id' => $userId]);
    $profile = $stmt->fetch() ?: [];

    // 3️⃣ Role-specific profile
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
=======
$userId = $_GET['userId'] ?? 0;

if (!$userId) {
    echo json_encode(['success' => false, 'message' => 'User ID required']);
    exit();
}

// Get user info
$stmt = $pdo->prepare("SELECT * FROM users WHERE id = :id");
$stmt->execute([':id' => $userId]);
$user = $stmt->fetch(PDO::FETCH_ASSOC);

if (!$user) {
    echo json_encode(['success' => false, 'message' => 'User not found']);
    exit();
}

// Get profile info
$stmt = $pdo->prepare("SELECT * FROM profiles WHERE user_id = :user_id");
$stmt->execute([':user_id' => $userId]);
$profile = $stmt->fetch(PDO::FETCH_ASSOC);

// Get role-specific profile
$roleTable = '';
switch ($user['role']) {
    case 'candidate': $roleTable = 'candidate_profiles'; break;
    case 'recruiter': $roleTable = 'recruiter_profiles'; break;
    case 'admin': $roleTable = 'admin_profiles'; break;
}

$roleProfile = [];
if ($roleTable) {
    $stmt = $pdo->prepare("SELECT * FROM $roleTable WHERE user_id = :user_id");
    $stmt->execute([':user_id' => $userId]);
    $roleProfile = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
}

echo json_encode([
    'success' => true,
    'profile' => array_merge(
        $profile ?: [],
        $roleProfile,
        ['role' => $user['role']]
    )
]);
?>
>>>>>>> upstream/main
