<?php
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
require_once __DIR__ . '/../config/database.php';


if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $data = json_decode(file_get_contents('php://input'), true);
    $job_id = $data['job_id'] ?? null;
    $applications = $data['applications'] ?? [];
    
    if (!$job_id || empty($applications)) {
        echo json_encode(["success" => false, "message" => "Invalid data"]);
        exit;
    }
    
    $database = new Database();
    $db = $database->getConnection();
    
    // Get job details for ranking
    $job_query = "SELECT title, description FROM jobs WHERE id = ?";
    $job_stmt = $db->prepare($job_query);
    $job_stmt->execute([$job_id]);
    $job = $job_stmt->fetch(PDO::FETCH_ASSOC);
    
    // Simple ranking algorithm (you can enhance this)
    $rankings = [];
    foreach ($applications as $application) {
        $score = calculateMatchScore($application, $job);
        
        $rankings[] = [
            'candidate_id' => $application['candidate_id'],
            'candidate_name' => $application['candidate_name'],
            'resume_filename' => $application['resume_filename'],
            'applied_at' => $application['applied_at'],
            'score' => $score
        ];
    }
    
    // Sort by score descending
    usort($rankings, function($a, $b) {
        return $b['score'] <=> $a['score'];
    });
    
    echo json_encode(["success" => true, "rankings" => $rankings]);
}

function calculateMatchScore($application, $job) {
    // Simple scoring based on keywords in resume filename (enhance this)
    $keywords = ['senior', 'experienced', 'python', 'react', 'javascript', 'php'];
    $score = 0.5; // Base score
    
    if ($application['resume_filename']) {
        $filename = strtolower($application['resume_filename']);
        $job_desc = strtolower($job['description']);
        
        // Check for keywords in resume filename
        foreach ($keywords as $keyword) {
            if (strpos($filename, $keyword) !== false) {
                $score += 0.1;
            }
            if (strpos($job_desc, $keyword) !== false && strpos($filename, $keyword) !== false) {
                $score += 0.2;
            }
        }
    }
    
    // Add some randomness for demo (replace with actual analysis)
    $score += mt_rand(0, 300) / 1000;
    
    // Cap at 1.0
    return min($score, 1.0);
}
?>