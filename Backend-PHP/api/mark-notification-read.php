<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';

$input = json_decode(file_get_contents('php://input'), true);
$notification_id = $input['notification_id'] ?? null;
$user_id = $input['user_id'] ?? null;

if (!$notification_id || !$user_id) {
    http_response_code(400);
    echo json_encode([
        "success" => false,
        "message" => "notification_id and user_id are required"
    ]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();

    $stmt = $db->prepare("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?");
    $stmt->execute([$notification_id, $user_id]);

    echo json_encode([
        "success" => true
    ]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to update notification",
        "error" => $e->getMessage()
    ]);
}
