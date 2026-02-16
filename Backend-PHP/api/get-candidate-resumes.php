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
    $database = new Database();
    $db = $database->getConnection();

    $query = "
        SELECT 
            resume_filename,
            MAX(uploaded_at) AS uploaded_at,
            MAX(display_name) AS display_name,
            MAX(source) AS source,
            MAX(id) AS id
        FROM (
            SELECT 
                id,
                resume_filename,
                uploaded_at,
                display_name,
                'upload' AS source
            FROM candidate_resumes
            WHERE candidate_id = :candidate_id

            UNION ALL

            SELECT 
                NULL AS id,
                resume_filename,
                applied_at AS uploaded_at,
                NULL AS display_name,
                'application' AS source
            FROM applications
            WHERE candidate_id = :candidate_id
              AND resume_filename IS NOT NULL
        ) AS combined
        WHERE resume_filename IS NOT NULL
        GROUP BY resume_filename
        ORDER BY uploaded_at DESC
    ";

    $stmt = $db->prepare($query);
    $stmt->execute([
        'candidate_id' => $candidate_id
    ]);

    $resumes = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo json_encode([
        "success" => true,
        "resumes" => $resumes
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to fetch resumes",
        "error" => $e->getMessage()
    ]);
}
?>
