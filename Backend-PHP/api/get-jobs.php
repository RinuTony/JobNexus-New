<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

require_once __DIR__ . '/../config/database.php';

try {
    // âœ… Railway PDO connection
    $database = new Database();
    $db = $database->getConnection();

    $sql = "
        SELECT 
            j.id,
            j.title,
            j.description,
            j.created_at,
            u.email AS recruiter_email
        FROM jobs j
        JOIN users u ON j.recruiter_id = u.id
        ORDER BY j.created_at DESC
    ";

    $stmt = $db->prepare($sql);
    $stmt->execute();

    $jobs = $stmt->fetchAll();

    echo json_encode([
        "success" => true,
        "jobs" => $jobs
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to fetch jobs"
    ]);
}
