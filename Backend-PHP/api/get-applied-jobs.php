<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Content-Type: application/json");

require_once __DIR__ . '/../config/database.php';

$candidate_id = $_GET['candidate_id'] ?? null;

if (!$candidate_id) {
    echo json_encode([
        "success" => false,
        "message" => "Candidate ID required"
    ]);
    exit;
}

try {
    // âœ… Railway PDO connection
    $database = new Database();
    $db = $database->getConnection();

    $query = "SELECT job_id, applied_at, status FROM applications WHERE candidate_id = ?";
    $stmt = $db->prepare($query);
    $stmt->execute([$candidate_id]);

    $applications = $stmt->fetchAll();

    echo json_encode([
        "success" => true,
        "applications" => $applications
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => $e->getMessage()
    ]);
}
