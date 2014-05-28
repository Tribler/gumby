library(ggplot2)
library(reshape)

my_graph <- function(name, hash) {
  df <- read.table(paste(hash, "_connections.txt", sep=""), header=T, quote="\"")

  candidates <- df[c('TIME', 'WALK_CANDIDATES', 'STUMBLE_CANDIDATES', 'INTRO_CANDIDATES', 'NONE_CANDIDATES')]
  candidates <- melt(candidates, id=c("TIME"))

  p <- ggplot(candidates, aes(TIME, value))
  p <- p + geom_line(aes(colour=variable))
  p <- p + ylim(0, max(30, candidates$value))

  p <- p + labs(title=paste(name, "candidates"),
                x="Time (seconds)",
                y="Candidates",
                colour="Candidate types")

  ggsave(file=paste(hash, "_candidates.png", sep=""),
         width=8, height=6, dpi=100)
  
  walks <- df[c('TIME', 'INCOMING_WALKS', 'OUTGOING_WALKS', 'WALK_SUCCESS')]
  walks <- melt(walks, id=c("TIME"))
  p <- ggplot(walks, aes(TIME, value, fill=variable))
  p <- p + geom_line(aes(colour=variable))
  p + labs(title=paste(name, "walker"),
           x="Time (seconds)",
           y="Walks",
           colour="Types")
  ggsave(file=paste(hash, "_walks.png", sep=""),
         width=8, height=6, dpi=100)
}

my_graph("All-channel community", "8164f55c2f828738fa779570e4605a81fec95c9d")
my_graph("Search community", "2782dc9253cef6cc9272ee8ed675c63743c4eb3a")

q(save="no")
