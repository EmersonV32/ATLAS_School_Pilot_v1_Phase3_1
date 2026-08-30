"use strict";

const header = document.querySelector("[data-header]");
const revealItems = document.querySelectorAll(".reveal");
const artworkImage = document.getElementById("featured-artwork");
const artworkDescription = document.getElementById("artwork-description");

const artworks = {
  mona: {
    src: "assets/mona-lisa.webp",
    alt: "Mona Lisa",
    description: "Begin with the familiar face, then ask about the painter, the landscape, or why the portrait still holds our attention.",
  },
  wave: {
    src: "assets/great-wave.webp",
    alt: "The Great Wave off Kanagawa",
    description: "Move from the force of the wave to the printmaking process, Mount Fuji, or the journey of this image around the world.",
  },
  ambassadors: {
    src: "assets/ambassadors.webp",
    alt: "The Ambassadors",
    description: "Explore the objects, the people, and the stretched skull that reveals itself only when the painting is viewed from another angle.",
  },
};

function updateHeader() {
  header.classList.toggle("scrolled", window.scrollY > 40);
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.14 });

revealItems.forEach((item) => observer.observe(item));
window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();

document.querySelectorAll("[data-artwork]").forEach((button) => {
  button.addEventListener("click", () => {
    const artwork = artworks[button.dataset.artwork];
    if (!artwork) return;
    artworkImage.src = artwork.src;
    artworkImage.alt = artwork.alt;
    artworkDescription.textContent = artwork.description;
    document.querySelectorAll("[data-artwork]").forEach((peer) => {
      const active = peer === button;
      peer.classList.toggle("active", active);
      peer.setAttribute("aria-pressed", String(active));
    });
  });
});
