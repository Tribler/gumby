library(ggplot2)
library(reshape)

my_graph <- function(name, hash) {
  connections <- read.table(paste(hash, "_connections.txt", sep=""), header=T, quote="\"")
  
  candidates <- connections
  candidates$B_ATTEMPTS <- candidates$B_SUCCESSES <- NULL
  candidates$C_ATTEMPTS <- candidates$C_SUCCESSES <- NULL
  mcandidates <- melt(candidates, id=c("TIME"))
  p <- ggplot(mcandidates, aes(TIME, value))
  p <- p + geom_line(aes(colour=variable))
  p <- p + ylim(0, max(30, mcandidates$value))
  p <- p + labs(title=paste(name, "candidates"),
                x="Time (seconds)",
                y="Candidates",
                colour="Candidate types")
  ggsave(file=paste(hash, "_candidates.png", sep=""),
         width=8, height=6, dpi=100)
  
  walks <- connections
  walks$VERIFIED_CANDIDATES <- NULL
  walks$WALK_CANDIDATES <- walks$STUMBLE_CANDIDATES <- NULL
  walks$INTRO_CANDIDATES <- walks$NONE_CANDIDATES <- NULL
  mwalks <- melt(walks, id=c("TIME"))
  p <- ggplot(mwalks, aes(TIME, value, fill=variable))
  p <- p + geom_line(aes(colour=variable))
  p + labs(title=paste(name, "walker"),
           x="Time (seconds)",
           y="Walks",
           colour="Types")
  ggsave(file=paste(hash, "_walks.png", sep=""),
         width=8, height=6, dpi=100)
}

my_graph("All-channel community", "8164f55c2f828738fa779570e4605a81fec95c9d")
my_graph("Barter community", "4fe1172862c649485c25b3d446337a35f389a2a2")
my_graph("Search community", "2782dc9253cef6cc9272ee8ed675c63743c4eb3a")

q(save="no")
