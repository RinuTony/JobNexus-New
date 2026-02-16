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

$user_id = $_GET['user_id'] ?? null;
$limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 20;

if (!$user_id) {
    echo json_encode([
        "success" => false,
        "message" => "user_id is required"
    ]);
    exit();
}

try {
    $database = new Database();
    $db = $database->getConnection();

    $query = "
        SELECT 
            n.id,
            n.user_id,
            n.application_id,
            n.job_id,
            n.status,
            n.message,
            n.is_read,
            n.created_at,
            j.title AS job_title
        FROM notifications n
        LEFT JOIN jobs j ON n.job_id = j.id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT ?
    ";

    $stmt = $db->prepare($query);
    $stmt->bindValue(1, $user_id, PDO::PARAM_INT);
    $stmt->bindValue(2, $limit, PDO::PARAM_INT);
    $stmt->execute();

    $notifications = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        "success" => true,
        "notifications" => $notifications
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to fetch notifications",
        "error" => $e->getMessage()
    ]);
}
