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

    $query = "
        SELECT a.id AS application_id, a.job_id, a.applied_at, a.status
        FROM applications a
        INNER JOIN (
            SELECT job_id, MAX(id) AS latest_application_id
            FROM applications
            WHERE candidate_id = ?
            GROUP BY job_id
        ) latest ON latest.latest_application_id = a.id
        WHERE a.candidate_id = ?
        ORDER BY a.applied_at DESC, a.id DESC
    ";
    $stmt = $db->prepare($query);
    $stmt->execute([$candidate_id, $candidate_id]);

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
