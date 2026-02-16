<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");

require_once __DIR__ . '/../config/database.php';

$recruiter_id = $_GET["recruiter_id"] ?? null;

if (!$recruiter_id) {
    echo json_encode([
        "success" => false,
        "message" => "recruiter_id is required"
    ]);
    exit;
}

try {
    // ✅ Railway PDO connection
    $database = new Database();
    $db = $database->getConnection();

    function fetchPdfLinks($filename) {
        if (empty($filename)) {
            return [];
        }

        $payload = json_encode(['filename' => $filename]);
        $ch = curl_init("http://localhost:5001/extract-links");
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);

        $response = curl_exec($ch);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error || !$response) {
            return [];
        }

        $data = json_decode($response, true);
        if (!$data || empty($data['success'])) {
            return [];
        }

        return $data['links'] ?? [];
    }

    $sql = "
    SELECT 
        a.id AS application_id,
        a.status,
        a.applied_at,
        a.resume_filename,  
        j.title AS job_title,
        j.id AS job_id,     
        NULLIF(TRIM(CONCAT(COALESCE(p.first_name, ''), ' ', COALESCE(p.last_name, ''))), '') AS candidate_name,
        u.email AS candidate_email,
        u.id AS candidate_id,
        r.resume_data AS resume_data
    FROM applications a
    JOIN jobs j ON a.job_id = j.id
    JOIN users u ON a.candidate_id = u.id
    LEFT JOIN profiles p ON u.id = p.user_id
    LEFT JOIN resumes r ON u.id = r.user_id
    WHERE j.recruiter_id = ?
    ORDER BY a.applied_at DESC
";

    $stmt = $db->prepare($sql);
    $stmt->execute([$recruiter_id]);

    $applications = $stmt->fetchAll();

    // Extract portfolio links from resume_data
    foreach ($applications as &$app) {
        $links = [];
        if (!empty($app['resume_data'])) {
            $decoded = json_decode($app['resume_data'], true);
            if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
                $personalInfo = $decoded['personalInfo'] ?? [];
                $linkedIn = $personalInfo['linkedIn'] ?? '';
                $portfolio = $personalInfo['portfolio'] ?? '';
                $website = $personalInfo['website'] ?? '';

                if (!empty($linkedIn)) {
                    $links[] = ['label' => 'LinkedIn', 'url' => $linkedIn];
                }
                if (!empty($portfolio)) {
                    $links[] = ['label' => 'Portfolio', 'url' => $portfolio];
                }
                if (!empty($website)) {
                    $links[] = ['label' => 'Website', 'url' => $website];
                }
            }
        }

        if (empty($links) && !empty($app['resume_filename'])) {
            $links = fetchPdfLinks($app['resume_filename']);
        }

        $app['portfolio_links'] = $links;
        unset($app['resume_data']);
    }
    unset($app);

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
