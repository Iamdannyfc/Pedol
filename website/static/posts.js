const commentlister = document.getElementById("commentlister");
const clshow = document.getElementById("clshow");
async function clshowview(pos) {
  clshow.style = "display: block;";
  commentlister.style = " top:50px;left:1px; animation: fadeOutComment 20s";
  setTimeout(() => {
    // clshow.style.display = "block";
    // commentlister.style = "animation: moveTop 5s";
    clshow.style.display = "none";
  }, 15000);
}

async function commentlisterview() {
  let comlisterpos = await commentlister.getBoundingClientRect().y;
  if (parseInt(comlisterpos) <= 30) {
    console.log(comlisterpos);
    clshowview(comlisterpos);
  }
}

window.onscroll = commentlisterview;
