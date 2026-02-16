<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
require_once __DIR__ . '/../config/database.php';


$recruiter_id = $_GET['recruiter_id'] ?? null;

if ($recruiter_id) {
    $database = new Database();
    $db = $database->getConnection();
    
    $query = "SELECT * FROM jobs WHERE recruiter_id = ? ORDER BY created_at DESC";
    $stmt = $db->prepare($query);
    $stmt->execute([$recruiter_id]);
    
    $jobs = [];
    while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
        $jobs[] = $row;
    }
    
    echo json_encode(["success" => true, "jobs" => $jobs]);
} else {
    echo json_encode(["success" => false, "message" => "Recruiter ID required"]);
}
?>