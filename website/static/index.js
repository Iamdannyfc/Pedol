// This function likes a post
// By Are Daniel
// .............................
// .............................
function like(postId, type, commentId = 0) {
  // check if it is a Comment or a post then return appropriate id
  function check(type, postId, commentId) {
    if (type == "c") {
      postId = commentId;
    }
    return parseInt(postId);
  }

  // Set all the needed variable
  const typeAndId = `${type}-${check(type, postId, commentId)}`;
  const likeCount = document.getElementById(`likes-count-${typeAndId}`);
  const likeButton = document.getElementById(`like-${typeAndId}`);
  likeButton.innerHTML = " . ";

  // Make a like api call
  fetch(`/api/like/${type}/${postId}/${parseInt(commentId)}`, {
    method: "POST",
  })
    .then((res) => res.json())
    .then((data) => {
      // change the button
      if (data["liked"] == true) {
        likeButton.innerHTML = " Unlike ";
      } else {
        likeButton.innerHTML = " Like ";
      }

      // change the count
      if (data["likes"] == 0) {
        likeCount.innerHTML = "";
      } else if (data["likes"] == 1) {
        likeCount.innerHTML = `<span id="likes-totalcount-${type}-${commentId}">1</span> Like`;
      } else {
        likeCount.innerHTML = `<span id="likes-totalcount-${type}-${commentId}">${data["likes"]}</span> Likes`;
      }
    })
    .catch((e) => alert("Could not like this post"));
}

// ..........................
// ...........................
// This function shares a post

function share(postId, type, commentId = 0) {
  // check if it is a Comment or a post then return appropriate id
  function check(type, postId, commentId) {
    if (type == "c") {
      postId = commentId;
    }
    return parseInt(postId);
  }

  // Set all the needed variable
  const typeAndId = `${type}-${check(type, postId, commentId)}`;
  const shareButton = document.getElementById(`share-${typeAndId}`);
  shareButton.innerHTML = " . ";

  // Make a share api call
  fetch(`/api/share/${type}/${postId}/${parseInt(commentId)}`, {
    method: "POST",
  })
    .then((res) => res.json())
    .then((data) => {
      // change the button
      console.log(data["shared"]);
      if (data["shared"] == true) {
        shareButton.innerHTML = " Unshare ";
      } else {
        shareButton.innerHTML = " Share ";
      }
    })
    .catch((e) => alert("Could not share this post"));
}
