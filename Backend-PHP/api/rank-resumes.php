<?php
header("Content-Type: application/json");
require_once __DIR__ . '/../config/database.php';

/**
 * Rank resumes using the same Python semantic matcher used by candidate match score.
 * Calls: POST /api/match-score-with-existing/{job_id}
 */

function postForm(string $url, array $fields, int $timeout = 25): array {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query($fields),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_CONNECTTIMEOUT => 8,
        CURLOPT_HTTPHEADER => [
            "Content-Type: application/x-www-form-urlencoded",
            "Accept: application/json",
        ],
    ]);

    $raw = curl_exec($ch);
    $curlErr = curl_error($ch);
    $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($raw === false) {
        return [
            "ok" => false,
            "status" => $httpCode,
            "error" => $curlErr ?: "Request failed",
            "data" => null,
        ];
    }

    $data = json_decode($raw, true);
    if (!is_array($data)) {
        return [
            "ok" => false,
            "status" => $httpCode,
            "error" => "Invalid JSON response",
            "data" => null,
        ];
    }

    return [
        "ok" => ($httpCode >= 200 && $httpCode < 300),
        "status" => $httpCode,
        "error" => null,
        "data" => $data,
    ];
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(["success" => false, "message" => "Invalid request method"]);
    exit;
}

$data = json_decode(file_get_contents('php://input'), true);
$job_id = $data['job_id'] ?? null;
$applications = $data['applications'] ?? [];

if (!$job_id || empty($applications)) {
    echo json_encode(["success" => false, "message" => "Invalid data"]);
    exit;
}

$database = new Database();
$db = $database->getConnection();

// Keep job existence check in PHP layer for fast feedback.
$job_query = "SELECT id, title, description FROM jobs WHERE id = ?";
$job_stmt = $db->prepare($job_query);
$job_stmt->execute([$job_id]);
$job = $job_stmt->fetch(PDO::FETCH_ASSOC);
if (!$job) {
    echo json_encode(["success" => false, "message" => "Job not found"]);
    exit;
}

$pythonApiBase = getenv("PYTHON_MATCH_API_BASE") ?: "http://localhost:8000";
$rankings = [];

foreach ($applications as $application) {
    $candidateId = isset($application['candidate_id']) ? (string)$application['candidate_id'] : '';
    if ($candidateId === '') {
        continue;
    }

    $resumeFilename = isset($application['resume_filename']) ? trim((string)$application['resume_filename']) : '';
    $payload = [
        "candidate_id" => $candidateId,
        "resume_type" => ($resumeFilename !== '' ? "uploaded" : "latest"),
    ];
    if ($resumeFilename !== '') {
        $payload["resume_filename"] = $resumeFilename;
    }

    $url = rtrim($pythonApiBase, "/") . "/api/match-score-with-existing/" . urlencode((string)$job_id);
    $result = postForm($url, $payload);

    $score = 0.0;
    $matchPercentage = 0.0;
    $scoreError = null;

    if ($result["ok"] && is_array($result["data"])) {
        $body = $result["data"];
        if (!empty($body["success"])) {
            $score = isset($body["similarity_score"]) ? (float)$body["similarity_score"] : 0.0;
            $matchPercentage = isset($body["match_percentage"]) ? (float)$body["match_percentage"] : round($score * 100, 1);
        } else {
            $scoreError = $body["detail"] ?? ($body["message"] ?? "Python scorer failed");
        }
    } else {
        $scoreError = $result["error"] ?: ("HTTP " . (string)$result["status"]);
    }

    $rankings[] = [
        'candidate_id' => $application['candidate_id'] ?? null,
        'candidate_name' => $application['candidate_name'] ?? 'Unknown Candidate',
        'resume_filename' => $application['resume_filename'] ?? '',
        'applied_at' => $application['applied_at'] ?? null,
        'score' => max(0.0, min(1.0, $score)),
        'match_percentage' => max(0.0, min(100.0, $matchPercentage)),
        'scoring_error' => $scoreError,
    ];
}

// Sort by score descending
usort($rankings, function($a, $b) {
    return ($b['score'] <=> $a['score']);
});

echo json_encode([
    "success" => true,
    "job_id" => $job_id,
    "job_title" => $job['title'] ?? '',
    "rankings" => $rankings
]);
?>
