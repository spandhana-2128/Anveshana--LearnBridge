async function processDubbing() {
  const videoFile = document.getElementById("videoFile").files[0];
  const language = document.getElementById("language").value;

  const formData = new FormData();
  formData.append("video", videoFile);
  formData.append("language", language);

  const response = await fetch("/video-dubbing", {
    method: "POST",
    body: formData,
  });

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "dubbed_video.mp4";
    a.click();
  } else {
    document.getElementById("dubbingStatus").textContent = "Dubbing failed.";
  }
}

async function summarizeVideo() {
  const videoURL = document.getElementById("videoURL").value;

  const response = await fetch("/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ video_url: videoURL }),
  });

  const data = await response.json();
  document.getElementById("summary").textContent = data.summary;
}

async function generateQuiz() {
  const transcript = document.getElementById("transcript").value;

  const response = await fetch("/generate-quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ transcript }),
  });

  const data = await response.json();
  const quizList = document.getElementById("quizQuestions");
  quizList.innerHTML = "";
  data.quiz.forEach((question) => {
    const li = document.createElement("li");
    li.textContent = question;
    quizList.appendChild(li);
  });
}
